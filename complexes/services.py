"""Сбор карточек жилищных комплексов из внутренней базы."""

from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
import logging

from django.db import OperationalError, ProgrammingError

from realestate.models import RealtyOffer

from .models import PartnerComplex
from .utils import load_gallery, normalize_complex_name, slugify_name

logger = logging.getLogger(__name__)

# Фоновые картинки для ЖК без загруженных фото (циклически).
PLACEHOLDER_IMAGES = [
    "https://images.unsplash.com/photo-1501045661006-fcebe0257c3f?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1460317442991-0ec209397118?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1501183638710-841dd1904471?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1491554150235-360c8a9149a0?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1505691723518-36a5ac3be353?auto=format&fit=crop&w=1200&q=80",
]


def _most_common(values):
    counter = Counter(values)
    return counter.most_common(1)[0][0] if counter else ""


def get_active_complexes():
    try:
        return list(PartnerComplex.objects.filter(is_active=True).order_by('name'))
    except (OperationalError, ProgrammingError) as exc:  # pragma: no cover
        logger.warning('PartnerComplex table unavailable: %s', exc)
        return []


def get_complex_summary(complexes=None):
    complexes = complexes if complexes is not None else get_active_complexes()
    active_count = len(complexes)
    apartments_total = sum((complex.apartments_count or 0) for complex in complexes)
    return {
        'active_count': active_count,
        'apartments_total': apartments_total,
    }


def _format_price_label(value: Decimal | None) -> str | None:
    if value is None:
        return None
    try:
        rounded = int(value.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except Exception:
        return None
    return f"от {rounded:,} ₽".replace(",", " ")


def get_active_complex_names():
    return [complex_instance.name for complex_instance in get_active_complexes()]


def get_complex_cards(complexes=None):
    complexes = complexes if complexes is not None else get_active_complexes()
    cards = []
    for idx, complex_instance in enumerate(complexes):
        district = complex_instance.district or "Район уточняется"
        metro = complex_instance.metro or "Метро уточняется"
        status = complex_instance.status or "Статус уточняется"
        price_from = complex_instance.price_label or "Цена уточняется"
        units = complex_instance.apartments_count or 0
        features = [
            f"Всего квартир: {units}",
            f"Метро: {metro}",
            f"Статус: {status}",
        ]
        slug = slugify_name(complex_instance.name)
        gallery = []
        try:
            gallery = load_gallery(slug)
        except Exception as exc:  # pragma: no cover
            logger.warning('Failed to load gallery for %s: %s', slug, exc)
        main_gallery = next((item for item in gallery if item.get("is_main")), None)
        hero_url = main_gallery["url"] if main_gallery else None
        hero_image = hero_url or PLACEHOLDER_IMAGES[idx % len(PLACEHOLDER_IMAGES)]
        cards.append(
            {
                "name": complex_instance.name,
                "district": district,
                "metro": metro,
                "status": status,
                "price_from": price_from,
                "units": units,
                "features": features,
                "image": hero_image,
                "gallery": gallery,
                "slug": slug,
                "description": complex_instance.description or "",
            }
        )
    return cards


def refresh_complex_data_from_offers():
    """Собирает актуальные цифры по ЖК на основе realestate.RealtyOffer."""
    complexes = {
        complex_instance.normalized_name: complex_instance
        for complex_instance in PartnerComplex.objects.filter(is_active=True)
    }
    if not complexes:
        return {'updated': 0, 'without_offers': 0, 'considered': 0}

    stats = defaultdict(lambda: {
        'count': 0,
        'prices': [],
        'districts': [],
        'metros': [],
    })
    offers = RealtyOffer.objects.exclude(building_name__isnull=True).exclude(building_name__exact="")
    for row in offers.values('building_name', 'price', 'district', 'metro_name'):
        normalized = normalize_complex_name(row['building_name'])
        if normalized not in complexes:
            continue
        data = stats[normalized]
        data['count'] += 1
        if row['price'] is not None:
            data['prices'].append(row['price'])
        if row['district']:
            data['districts'].append(row['district'])
        if row['metro_name']:
            data['metros'].append(row['metro_name'])

    updated = 0
    for normalized, payload in stats.items():
        complex_instance = complexes.get(normalized)
        if not complex_instance:
            continue
        min_price = min(payload['prices']) if payload['prices'] else None
        price_label = _format_price_label(min_price)
        district = _most_common(payload['districts']) or None
        metro = _most_common(payload['metros']) or None
        apartments_count = payload['count']
        fields_to_update = {}
        if complex_instance.apartments_count != apartments_count:
            fields_to_update['apartments_count'] = apartments_count
        if price_label and complex_instance.price_label != price_label:
            fields_to_update['price_label'] = price_label
        if district and complex_instance.district != district:
            fields_to_update['district'] = district
        if metro and complex_instance.metro != metro:
            fields_to_update['metro'] = metro
        if fields_to_update:
            for field, value in fields_to_update.items():
                setattr(complex_instance, field, value)
            complex_instance.save(update_fields=[*fields_to_update.keys(), 'updated_at'])
            updated += 1

    without_offers = len(set(complexes) - set(stats))
    return {
        'updated': updated,
        'without_offers': without_offers,
        'considered': len(stats),
    }
