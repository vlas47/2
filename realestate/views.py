import xml.etree.ElementTree as ET
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.management import call_command
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from django.urls import reverse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from .models import RealtyOffer

SETL_CACHE = {'path': None, 'mtime': None, 'data': {}}


class RealEstateDashboardView(TemplateView):
    """Простая служебная страница с краткой статистикой базы предложений."""

    template_name = 'realestate/dashboard.html'
    paginate_by = None  # переопределяется в наследниках при необходимости
    _max_without_pagination = 200

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self._build_queryset()
        context['offers_total'] = RealtyOffer.objects.count()
        context['filtered_total'] = queryset.count()
        context['view_mode'] = 'table'
        context['filters'] = self.request.GET
        context['order'] = self.request.GET.get('order', '-last_update_date')
        base_query = self.request.GET.copy()
        base_query.pop('order', None)
        base_query.pop('page', None)
        context['base_query'] = base_query.urlencode()
        context['sort_options'] = {
            '-last_update_date': 'По обновлению ',
            'last_update_date': 'По обновлению ',
            'price': 'Цена ',
            '-price': 'Цена ',
            'rooms': 'Комнаты ',
            '-rooms': 'Комнаты ',
            'area': 'Площадь ',
            '-area': 'Площадь ',
        }

        context['district_options'] = list(
            RealtyOffer.objects.exclude(district__isnull=True)
            .exclude(district__exact='')
            .values_list('district', flat=True)
            .distinct()
            .order_by('district')
        )
        context['metro_options'] = list(
            RealtyOffer.objects.exclude(metro_name__isnull=True)
            .exclude(metro_name__exact='')
            .values_list('metro_name', flat=True)
            .distinct()
            .order_by('metro_name')
        )
        context['property_type_options'] = list(
            RealtyOffer.objects.exclude(property_type__isnull=True)
            .exclude(property_type__exact='')
            .values_list('property_type', flat=True)
            .distinct()
            .order_by('property_type')
        )

        page_obj = None
        if self.paginate_by:
            paginator = Paginator(queryset, self.paginate_by)
            page_number = self.request.GET.get('page') or 1
            page_obj = paginator.get_page(page_number)
            offers = list(page_obj.object_list)
        else:
            offers = list(queryset[: self._max_without_pagination])

        fallback = self._load_fallback_data([offer.internal_id for offer in offers])
        for offer in offers:
            fb = fallback.get(offer.internal_id, {})
            offer.extra = fb  # дополнительные поля из XML, которых нет в модели
            offer.metro_time_on_foot = offer.metro_time_on_foot or fb.get('metro_time_on_foot')
            offer.metro_time_on_transport = offer.metro_time_on_transport or fb.get('metro_time_on_transport')
            offer.decoration_type = offer.decoration_type or fb.get('decoration_type')
            offer.building_state = offer.building_state or fb.get('building_state')
            offer.building_year = offer.building_year or fb.get('building_year')
            ptype = (
                (offer.property_type or '').lower()
                or (offer.extra.get('property_type', '') or '').lower()
                or (offer.extra.get('category', '') or '').lower()
            )
            offer.is_parking = 'паркин' in ptype
            offer.is_commercial = 'коммер' in ptype
            offer.is_apartments = (
                getattr(offer, 'is_apartments', False)
                or str(offer.extra.get('apartments', '')).lower() in {'1', 'true', 'yes', 'да'}
            )
        context['offers'] = offers
        context['paginator'] = page_obj.paginator if page_obj else None
        context['page_obj'] = page_obj
        query_without_page = self.request.GET.copy()
        query_without_page.pop('page', None)
        context['query_without_page'] = query_without_page.urlencode()
        return context

    def _build_queryset(self):
        params = self.request.GET
        qs = RealtyOffer.objects.all()
        search = params.get('q')
        if search:
            qs = qs.filter(
                Q(address__icontains=search)
                | Q(building_name__icontains=search)
                | Q(locality_name__icontains=search)
            )
        region = params.get('region')
        if region:
            qs = qs.filter(region__icontains=region)
        district = params.get('district')
        if district:
            qs = qs.filter(district__icontains=district)
        metro = params.get('metro')
        if metro:
            qs = qs.filter(metro_name__icontains=metro)
        rooms = params.get('rooms')
        if rooms and rooms.isdigit():
            qs = qs.filter(rooms=int(rooms))
        prop_type = params.get('type')
        if prop_type:
            qs = qs.filter(property_type__icontains=prop_type)
        property_type = params.get('property_type')
        if property_type:
            qs = qs.filter(property_type__iexact=property_type)
        category = params.get('category')
        if category:
            if category == 'new':
                qs = qs.filter(is_new_flat=True)
            elif category == 'secondary':
                qs = qs.filter(is_new_flat=False, property_type__icontains='квартира')
            elif category == 'land':
                qs = qs.filter(property_type__icontains='участок')
            elif category == 'house':
                qs = qs.filter(property_type__icontains='дом')
        min_price = params.get('price_min')
        if min_price and min_price.isdigit():
            qs = qs.filter(price__gte=min_price)
        max_price = params.get('price_max')
        if max_price and max_price.isdigit():
            qs = qs.filter(price__lte=max_price)
        photo_only = params.get('photo') == 'on'
        if photo_only:
            qs = qs.exclude(photos__isnull=True).exclude(photos__exact='')

        order = params.get('order', '-last_update_date')
        allowed = {
            'price',
            '-price',
            'rooms',
            '-rooms',
            'area',
            '-area',
            'last_update_date',
            '-last_update_date',
        }
        if order not in allowed:
            order = '-last_update_date'
        return qs.order_by(order)

    def _load_fallback_data(self, internal_ids):
        """Подтягивает недостающие поля напрямую из исходного XML.

        Данные кешируются в памяти (по пути и mtime файла), чтобы не парсить XML при каждом запросе.
        """
        feed_path = Path(settings.BASE_DIR) / 'Setl_XML'
        if not feed_path.exists():
            return {}

        target_ids = {val for val in internal_ids if val}
        if not target_ids:
            return {}

        stat = feed_path.stat()
        if SETL_CACHE['path'] != feed_path or SETL_CACHE['mtime'] != stat.st_mtime:
            SETL_CACHE['data'] = self._parse_full_feed(feed_path)
            SETL_CACHE['path'] = feed_path
            SETL_CACHE['mtime'] = stat.st_mtime

        cache_data = SETL_CACHE['data']
        return {iid: cache_data.get(iid, {}) for iid in target_ids}

    def _parse_full_feed(self, feed_path: Path):
        """Читает весь XML и собирает словарь по internal-id со всеми найденными полями."""
        ns = '{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}'

        def tag(name: str) -> str:
            return f'{ns}{name}'

        def get_text(element, name):
            if element is None:
                return None
            node = element.find(name)
            return node.text.strip() if node is not None and node.text else None

        result = {}
        context = ET.iterparse(feed_path, events=('end',))
        for _, elem in context:
            if elem.tag != tag('Offer'):
                continue
            internal_id = elem.get('internal-id')
            if not internal_id:
                elem.clear()
                continue

            location = elem.find(tag('location'))
            metro = elem.find(tag('metro'))
            price = elem.find(tag('price'))
            images = elem.findall(tag('image'))
            room_spaces = []
            for space in elem.findall(tag('room-space')):
                val = get_text(space, tag('value'))
                unit = get_text(space, tag('unit'))
                if val:
                    room_spaces.append({'value': val, 'unit': unit})

            plan_image = None
            floor_image = None
            photo_urls = []
            for img in images:
                if img.get('tag') == 'plan' and img.text:
                    plan_image = img.text
                elif img.get('tag') == 'floor' and img.text:
                    floor_image = img.text
                elif img.text:
                    photo_urls.append(img.text)

            result[internal_id] = {
                'internal_id': internal_id,
                'case_id': get_text(elem, tag('caseid')),
                'deal_type': get_text(elem, tag('type')),
                'property_type': get_text(elem, tag('property-type')),
                'category': get_text(elem, tag('category')),
                'creation_date': get_text(elem, tag('creation-date')),
                'last_update_date': get_text(elem, tag('last-update-date')),
                'country': get_text(location, tag('country')) if location is not None else None,
                'region': get_text(location, tag('region')) if location is not None else None,
                'district': get_text(location, tag('district')) if location is not None else None,
                'locality_name': get_text(location, tag('locality-name')) if location is not None else None,
                'sub_locality_name': get_text(location, tag('sub-locality-name')) if location is not None else None,
                'address': get_text(location, tag('address')) if location is not None else None,
                'latitude': get_text(location, tag('latitude')) if location is not None else None,
                'longitude': get_text(location, tag('longitude')) if location is not None else None,
                'deal_status': get_text(elem, tag('deal-status')),
                'deal_state': get_text(elem, tag('deal-state')),
                'metro_name': get_text(metro, tag('name')) if metro is not None else None,
                'metro_time_on_foot': get_text(metro, tag('time-on-foot')) if metro is not None else None,
                'metro_time_on_transport': get_text(metro, tag('time-on-transport')) if metro is not None else None,
                'price_value': get_text(price, tag('value')) if price is not None else None,
                'price_base': get_text(price, tag('basecost')) if price is not None else None,
                'price_cost': get_text(price, tag('cost')) if price is not None else None,
                'currency': get_text(price, tag('currency')) if price is not None else None,
                'area_total': get_text(elem, tag('area') + '/' + tag('value')),
                'area_living': get_text(elem, tag('living-space') + '/' + tag('value')),
                'area_kitchen': get_text(elem, tag('kitchen-space') + '/' + tag('value')),
                'area_lot': get_text(elem, tag('lot-area') + '/' + tag('value')),
                'area_balcony': get_text(elem, tag('balcony-area') + '/' + tag('value')),
                'rooms': get_text(elem, tag('rooms')),
                'floor': get_text(elem, tag('floor')),
                'floors_total': get_text(elem, tag('floors-total')),
                'ceiling_height': get_text(elem, tag('ceiling-height')),
                'ceiling_height_to': get_text(elem, tag('ceiling-height-to')),
                'new_flat': get_text(elem, tag('new-flat')),
                'apartments': get_text(elem, tag('apartments')),
                'studio': get_text(elem, tag('studio')),
                'brand': get_text(elem, tag('brand')),
                'building_id': get_text(elem, tag('building-id')),
                'building_name': get_text(elem, tag('building-name')),
                'building_state': get_text(elem, tag('building-state')),
                'building_phase': get_text(elem, tag('building-phase')),
                'building_type': get_text(elem, tag('building-type')),
                'building_section': get_text(elem, tag('building-section')),
                'building_material': get_text(elem, tag('building-material')),
                'building_year': get_text(elem, tag('built-year')),
                'assignment': get_text(elem, tag('assignment')),
                'entrance': get_text(elem, tag('entrance')),
                'section': get_text(elem, tag('section')),
                'decoration_type_id': get_text(elem, tag('decoration-type-id')),
                'decoration_type': get_text(elem, tag('decoration-type')),
                'number_flat': get_text(elem, tag('number-flat')),
                'renovation': get_text(elem, tag('renovation')),
                'plan_image': plan_image,
                'floor_image': floor_image,
                'photos': photo_urls,
                'room_spaces': room_spaces,
                'description': get_text(elem, tag('description')),
            }
            elem.clear()
        return result


class RealEstateCardsView(RealEstateDashboardView):
    """Альтернативное представление в виде карточек."""

    template_name = 'realestate/cards.html'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_mode'] = 'cards'
        return context


def check_url(url: str, timeout: float = 5.0) -> bool:
    req = Request(url, method="HEAD")
    try:
        with urlopen(req, timeout=timeout) as resp:  # nosec B310
            return resp.status < 400
    except (HTTPError, URLError):
        return False
    except Exception:
        return False


class CleanPhotosView(TemplateView):
    """Одноразовая ручка для очистки битых ссылок на фото."""

    def get(self, request, *args, **kwargs):
        limit = int(request.GET.get('limit', 200))
        timeout = float(request.GET.get('timeout', 5.0))
        qs = (
            RealtyOffer.objects.exclude(photos__isnull=True)
            .exclude(photos__exact="")
            .order_by('id')[:limit]
        )
        processed = 0
        changed = 0
        removed = 0
        for offer in qs:
            processed += 1
            photos = [line.strip() for line in offer.photos.splitlines() if line.strip()]
            if not photos:
                continue
            good = [p for p in photos if check_url(p, timeout=timeout)]
            if len(good) != len(photos):
                removed += len(photos) - len(good)
                changed += 1
                offer.photos = "\n".join(good)
                offer.save(update_fields=['photos'])
        if changed:
            messages.success(
                request,
                f"Чистка фото: проверено {processed}, обновлено {changed} записей, удалено ссылок {removed}.",
            )
        else:
            messages.info(request, f"Чистка фото: проверено {processed}, изменений нет.")
        referer = request.META.get('HTTP_REFERER') or reverse('realestate:dashboard')
        return HttpResponseRedirect(referer)


class CleanDuplicatesView(TemplateView):
    """Удаляет дубликаты по (адрес, номер квартиры, площадь), оставляя последний по обновлению."""

    def get(self, request, *args, **kwargs):
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
                (offer.address or "").strip().lower(),
                (offer.number_flat or "").strip().lower(),
                str(offer.area_total),
            )
            if key in seen:
                to_delete.append(offer.id)
            else:
                seen[key] = offer.id

        if to_delete:
            RealtyOffer.objects.filter(id__in=to_delete).delete()
            messages.success(request, f"Чистка дублей: удалено {len(to_delete)} записей.")
        else:
            messages.info(request, "Чистка дублей: совпадений не найдено.")

        referer = request.META.get('HTTP_REFERER') or reverse('realestate:dashboard')
        return HttpResponseRedirect(referer)


class ImportSetlView(TemplateView):
    """Импортирует данные из указанного XML-файла (по умолчанию Setl_XML в корне)."""

    def post(self, request, *args, **kwargs):
        upload = request.FILES.get("file")
        uploaded_path = None
        if upload:
            filename = Path(upload.name).name
            uploaded_path = Path(settings.BASE_DIR) / filename
            with uploaded_path.open("wb+") as tmp:
                for chunk in upload.chunks():
                    tmp.write(chunk)
            path = str(uploaded_path)
        else:
            path = request.POST.get("path") or "Setl_XML"
        try:
            call_command("import_setl", path=path)
            if upload:
                messages.success(request, f"Импортирован файл {upload.name}.")
            else:
                messages.success(request, f"Импорт из {path} завершён.")
        except Exception as exc:  # pragma: no cover
            messages.error(request, f"Ошибка импорта: {exc}")
            if uploaded_path and uploaded_path.exists():
                uploaded_path.unlink(missing_ok=True)
        referer = request.META.get("HTTP_REFERER") or reverse("realestate:dashboard")
        return HttpResponseRedirect(referer)

    def get(self, request, *args, **kwargs):
        referer = request.META.get("HTTP_REFERER") or reverse("realestate:dashboard")
        return HttpResponseRedirect(referer)
