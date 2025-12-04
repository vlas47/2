import logging
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from django.core.management.base import BaseCommand
from django.db import transaction

from realestate.models import RealtyOffer

logger = logging.getLogger(__name__)


def check_url(url: str, timeout: float = 5.0) -> bool:
    """Return True if URL responds with status < 400."""
    req = Request(url, method="HEAD")
    try:
        with urlopen(req, timeout=timeout) as resp:  # nosec: B310 controlled input
            return resp.status < 400
    except HTTPError as exc:
        logger.debug("HTTPError for %s: %s", url, exc)
        return False
    except URLError as exc:
        logger.debug("URLError for %s: %s", url, exc)
        return False
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Unexpected error for %s: %s", url, exc)
        return False


class Command(BaseCommand):
    help = "Проверяет ссылки на фото в RealtyOffer.photos и удаляет нерабочие."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Сколько записей проверять за запуск (по умолчанию 500).",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=5.0,
            help="Таймаут запроса к фото, сек (по умолчанию 5.0).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать, какие ссылки будут удалены, без сохранения.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        timeout = options["timeout"]
        dry_run = options["dry_run"]

        qs = (
            RealtyOffer.objects.exclude(photos__isnull=True)
            .exclude(photos__exact="")
            .order_by("id")[:limit]
        )

        processed = 0
        changed = 0
        removed_links = 0

        for offer in qs:
            processed += 1
            photos = [line.strip() for line in offer.photos.splitlines() if line.strip()]
            if not photos:
                continue

            good, bad = [], []
            for url in photos:
                if check_url(url, timeout=timeout):
                    good.append(url)
                else:
                    bad.append(url)

            if bad:
                removed_links += len(bad)
                changed += 1
                self.stdout.write(
                    f"[{offer.id}] удаляем {len(bad)} битых ссылок из {len(photos)}"
                )
                if not dry_run:
                    offer.photos = "\n".join(good)
                    offer.save(update_fields=["photos"])

        summary = f"Проверено записей: {processed}, с изменениями: {changed}, удалено ссылок: {removed_links}"
        if dry_run:
            summary += " (dry-run)"
        self.stdout.write(summary)
