import logging
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from realestate.models import RealtyOffer

logger = logging.getLogger(__name__)


def norm(value: str) -> str:
    return (value or "").strip().lower()


class Command(BaseCommand):
    help = (
        "Удаляет дубликаты RealtyOffer по (адрес, номер квартиры, площадь). "
        "Оставляет последнюю запись (по last_update_date, затем по id)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показать, что будет удалено, но не удалять.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        qs = (
            RealtyOffer.objects.exclude(address__isnull=True)
            .exclude(address__exact="")
            .exclude(number_flat__isnull=True)
            .exclude(number_flat__exact="")
            .exclude(area_total__isnull=True)
            .order_by("address", "number_flat", "area_total", "-last_update_date", "-id")
        )

        seen = {}
        to_delete = []
        for offer in qs:
            key = (
                norm(offer.address),
                norm(offer.number_flat),
                str(offer.area_total.quantize(Decimal("0.01")) if offer.area_total else offer.area_total),
            )
            if key in seen:
                to_delete.append(offer.id)
            else:
                seen[key] = offer.id

        total = len(to_delete)
        if total == 0:
            self.stdout.write("Дубликатов не найдено.")
            return

        self.stdout.write(f"Найдено дубликатов: {total}")

        if dry_run:
            self.stdout.write("Режим dry-run: удаление не выполняется.")
            return

        with transaction.atomic():
            deleted, _ = RealtyOffer.objects.filter(id__in=to_delete).delete()
        self.stdout.write(f"Удалено записей: {deleted}")
