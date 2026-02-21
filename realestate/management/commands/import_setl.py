from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from realestate.models import RealtyOffer

NS = '{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}'
TRUE_VALUES = {'да', 'yes', 'true', '1', 'y'}


def tag(name: str) -> str:
    return f'{NS}{name}'


def get_text(element: ET.Element, path: str) -> Optional[str]:
    node = element.find(path)
    return node.text.strip() if node is not None and node.text else None


def as_decimal(value: Optional[str]) -> Optional[Decimal]:
    if value in (None, ''):
        return None
    try:
        cleaned = value.replace(',', '.')
        return Decimal(cleaned)
    except Exception:
        return None


def as_int(value: Optional[str]) -> Optional[int]:
    if value in (None, ''):
        return None
    try:
        cleaned = value.replace(',', '.')
        return int(Decimal(cleaned))
    except Exception:
        return None


def as_datetime(value: Optional[str]) -> Optional[dt.datetime]:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def as_bool(value: Optional[str]) -> bool:
    if not value:
        return False
    return value.strip().lower() in TRUE_VALUES


class Command(BaseCommand):
    help = 'Импортирует объекты из XML-фида Setl в таблицу realestate_realityoffer'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            default='Setl_XML',
            help='Путь к файлу фида (по умолчанию Setl_XML в корне проекта)',
        )

    def handle(self, *args, **options):
        feed_path = Path(options['path'])
        if not feed_path.exists():
            raise CommandError(f'Файл {feed_path} не найден')

        imported = 0
        context = ET.iterparse(feed_path, events=('end',))
        for _, elem in context:
            if elem.tag != tag('Offer'):
                continue
            data = self._parse_offer(elem)
            if not data:
                elem.clear()
                continue
            with transaction.atomic():
                RealtyOffer.objects.update_or_create(
                    internal_id=data.pop('internal_id'),
                    defaults=data,
                )
            imported += 1
            elem.clear()
        self.stdout.write(self.style.SUCCESS(f'Импортировано объектов: {imported}'))

    def _parse_offer(self, elem: ET.Element) -> Optional[dict]:
        internal_id = elem.get('internal-id')
        if not internal_id:
            return None

        location = elem.find(tag('location'))
        metro = elem.find(tag('metro'))
        price = elem.find(tag('price'))

        data = {
            'internal_id': internal_id,
            'case_id': get_text(elem, tag('caseid')),
            'deal_type': get_text(elem, tag('type')),
            'property_type': get_text(elem, tag('property-type')),
            'category': get_text(elem, tag('category')),
            'deal_status': get_text(elem, tag('deal-status')),
            'deal_state': get_text(elem, tag('deal-state')),
            'creation_date': as_datetime(get_text(elem, tag('creation-date'))),
            'last_update_date': as_datetime(get_text(elem, tag('last-update-date'))),
            'country': get_text(location, tag('country')) if location is not None else None,
            'region': get_text(location, tag('region')) if location is not None else None,
            'district': get_text(location, tag('district')) if location is not None else None,
            'locality_name': get_text(location, tag('locality-name'))
            if location is not None
            else None,
            'sub_locality_name': get_text(location, tag('sub-locality-name'))
            if location is not None
            else None,
            'address': get_text(location, tag('address')) if location is not None else None,
            'latitude': as_decimal(get_text(location, tag('latitude'))) if location is not None else None,
            'longitude': as_decimal(get_text(location, tag('longitude'))) if location is not None else None,
            'metro_name': get_text(metro, tag('name')) if metro is not None else None,
            'metro_time_on_foot': as_int(get_text(metro, tag('time-on-foot')))
            if metro is not None
            else None,
            'metro_time_on_transport': as_int(get_text(metro, tag('time-on-transport')))
            if metro is not None
            else None,
            'price': as_decimal(get_text(price, tag('value'))) if price is not None else None,
            'price_base': as_decimal(get_text(price, tag('basecost'))) if price is not None else None,
            'price_cost': as_decimal(get_text(price, tag('cost'))) if price is not None else None,
            'currency': get_text(price, tag('currency')) if price is not None else None,
            'area_total': as_decimal(get_text(elem, tag('area') + '/' + tag('value'))),
            'area_living': as_decimal(get_text(elem, tag('living-space') + '/' + tag('value'))),
            'area_kitchen': as_decimal(get_text(elem, tag('kitchen-space') + '/' + tag('value'))),
            'area_lot': as_decimal(get_text(elem, tag('lot-area') + '/' + tag('value'))),
            'area_balcony': as_decimal(get_text(elem, tag('balcony-area') + '/' + tag('value'))),
            'rooms': as_int(get_text(elem, tag('rooms'))),
            'floor': as_int(get_text(elem, tag('floor'))),
            'floors_total': as_int(get_text(elem, tag('floors-total'))),
            'ceiling_height': as_decimal(get_text(elem, tag('ceiling-height'))),
            'is_new_flat': as_bool(get_text(elem, tag('new-flat'))),
            'is_apartments': as_bool(get_text(elem, tag('apartments'))),
            'is_studio': as_bool(get_text(elem, tag('studio'))),
            'building_id': get_text(elem, tag('building-id')),
            'building_name': get_text(elem, tag('building-name')),
            'building_state': get_text(elem, tag('building-state')),
            'building_phase': get_text(elem, tag('building-phase')),
            'building_type': get_text(elem, tag('building-type')),
            'building_section': get_text(elem, tag('building-section')),
            'building_material': get_text(elem, tag('building-material')),
            'building_year': get_text(elem, tag('built-year')),
            'brand': get_text(elem, tag('brand')),
            'decoration_type': get_text(elem, tag('decoration-type')),
            'number_flat': get_text(elem, tag('number-flat')),
            'entrance': get_text(elem, tag('entrance')),
            'section': get_text(elem, tag('section')),
            'photos': '\n'.join(img.text for img in elem.findall(tag('image')) if img.text),
            'description': get_text(elem, tag('description')),
        }
        return data
