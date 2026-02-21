from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from complexes.models import PartnerComplex
from complexes.utils import gallery_dir, normalize_complex_name, slugify_name

REALTY_NAMESPACE = "http://webmaster.yandex.ru/schemas/feed/realty/2010-06"
OFFER_TAG = f"{{{REALTY_NAMESPACE}}}Offer"

STATUS_LABELS = {
    "unfinished": "Строится",
    "hand-over": "Сдан",
}

DEFAULT_PROPERTY_TYPES = {"квартира", "апартамент"}


def ns_tag(name: str) -> str:
    return f"{{{REALTY_NAMESPACE}}}{name}"


def clean_text(value: str | None) -> str:
    return value.strip() if value else ""


def pick_value(*value_lists: Iterable[str]) -> str:
    for values in value_lists:
        filtered = [value for value in values if value]
        if not filtered:
            continue
        counter = Counter(filtered)
        return counter.most_common(1)[0][0]
    return ""


def parse_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def format_price_label(price: Decimal | None) -> str:
    if price is None:
        return ""
    amount = int(price.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"от {amount:,} ₽".replace(",", " ")


class Command(BaseCommand):
    help = "Заполняет PartnerComplex данными из XML-фида Setl и создаёт папки для галерей."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="Setl_XML",
            help="Путь к файлу с выгрузкой Setl (по умолчанию Setl_XML в корне проекта).",
        )
        parser.add_argument(
            "--property-types",
            nargs="+",
            default=sorted(DEFAULT_PROPERTY_TYPES),
            help="Какие property-type учитывать (по умолчанию квартиры и апартаменты).",
        )
        parser.add_argument(
            "--deactivate-missing",
            action="store_true",
            help="Пометить как неактуальные записи, которых нет во входном файле.",
        )
        parser.add_argument(
            "--update-active",
            action="store_true",
            help="Принудительно обновлять флаг актуальности (по умолчанию сохраняем ручные правки).",
        )
        parser.add_argument(
            "--skip-photo-dirs",
            action="store_true",
            help="Не создавать каталоги в static/complexes_photos после импорта.",
        )

    def handle(self, *args, **options):
        source = Path(options["source"])
        if not source.is_absolute():
            source = Path(settings.BASE_DIR) / source
        if not source.exists():
            raise CommandError(f"Файл {source} не найден.")

        property_types = {value.lower() for value in options["property_types"] if value}
        if not property_types:
            property_types = set(DEFAULT_PROPERTY_TYPES)

        complexes = self._collect_complexes(source, property_types)
        if not complexes:
            raise CommandError("Во входном файле не найдено ни одного подходящего ЖК.")

        created, updated, active_slugs = self._save_complexes(
            complexes,
            update_active=options["update_active"],
        )
        self.stdout.write(
            self.style.SUCCESS(f"Импортировано {created + updated} ЖК (создано {created}, обновлено {updated}).")
        )

        if options["deactivate_missing"]:
            missing = PartnerComplex.objects.exclude(normalized_name__in=complexes.keys())
            deactivated = missing.update(is_active=False)
            if deactivated:
                self.stdout.write(self.style.WARNING(f"Деактивировано {deactivated} отсутствующих в фиде ЖК."))

        if not options["skip_photo_dirs"]:
            self._ensure_photo_dirs(active_slugs)

    def _collect_complexes(self, source: Path, allowed_types: set[str]) -> dict[str, dict]:
        aggregated: dict[str, dict] = {}
        for event, element in ET.iterparse(source, events=("end",)):
            if element.tag != OFFER_TAG:
                continue

            property_type = clean_text(element.findtext(ns_tag("property-type"))).lower()
            if allowed_types and property_type not in allowed_types:
                element.clear()
                continue

            name = clean_text(element.findtext(ns_tag("building-name")))
            if not name:
                element.clear()
                continue

            normalized = normalize_complex_name(name)
            entry = aggregated.setdefault(
                normalized,
                {
                    "name": name,
                    "districts": [],
                    "sub_localities": [],
                    "localities": [],
                    "metros": [],
                    "statuses": [],
                    "prices": [],
                    "count": 0,
                },
            )
            if not entry.get("name"):
                entry["name"] = name
            entry["count"] += 1

            district = clean_text(element.findtext(f"{ns_tag('location')}/{ns_tag('district')}"))
            sub_locality = clean_text(element.findtext(f"{ns_tag('location')}/{ns_tag('sub-locality-name')}"))
            locality = clean_text(element.findtext(f"{ns_tag('location')}/{ns_tag('locality-name')}"))
            if district:
                entry["districts"].append(district)
            if sub_locality:
                entry["sub_localities"].append(sub_locality)
            if locality:
                entry["localities"].append(locality)

            for metro_node in element.findall(ns_tag("metro")):
                metro_name = clean_text(metro_node.findtext(ns_tag("name")))
                if metro_name:
                    entry["metros"].append(metro_name)

            state = clean_text(element.findtext(ns_tag("building-state"))).lower()
            if state:
                entry["statuses"].append(STATUS_LABELS.get(state, state))

            price_value = parse_decimal(clean_text(element.findtext(f"{ns_tag('price')}/{ns_tag('value')}")))
            if price_value is None:
                price_value = parse_decimal(clean_text(element.findtext(f"{ns_tag('price')}/{ns_tag('cost')}")))
            if price_value is not None:
                entry["prices"].append(price_value)

            element.clear()

        return dict(sorted(aggregated.items(), key=lambda item: item[1]["name"].lower()))

    def _save_complexes(self, complexes: dict[str, dict], update_active: bool) -> tuple[int, int, list[str]]:
        created = updated = 0
        active_slugs: list[str] = []
        with transaction.atomic():
            for normalized, payload in complexes.items():
                name = payload["name"]
                slug = slugify_name(name)
                district = pick_value(payload["districts"], payload["sub_localities"], payload["localities"])
                metro = pick_value(payload["metros"])
                status = pick_value(payload["statuses"])
                price_label = format_price_label(min(payload["prices"])) if payload["prices"] else ""
                obj, was_created = PartnerComplex.objects.get_or_create(
                    normalized_name=normalized,
                    defaults={"name": name},
                )
                obj.name = name
                obj.slug = slug
                obj.apartments_count = payload["count"]
                obj.district = district or None
                obj.metro = metro or None
                obj.status = status or None
                obj.price_label = price_label or None
                if update_active or was_created:
                    obj.is_active = True
                obj.save()
                if obj.is_active:
                    active_slugs.append(obj.slug)
                if was_created:
                    created += 1
                else:
                    updated += 1
        return created, updated, active_slugs

    def _ensure_photo_dirs(self, slugs: list[str]) -> None:
        created_dirs = 0
        for slug in slugs:
            path = gallery_dir(slug)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                created_dirs += 1
        if created_dirs:
            self.stdout.write(f"Создано {created_dirs} папок для галерей ЖК.")
