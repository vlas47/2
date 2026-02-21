from django.db.models import Count, Min, Max
from django.http import Http404
from django.views.generic import TemplateView

from realestate.models import RealtyOffer
from realestate.views import RealEstateDashboardView
from complexes.services import get_complex_cards, get_active_complexes
from complexes.utils import load_gallery, slugify_name
from complexes.services import PLACEHOLDER_IMAGES
from complexes.models import PartnerComplex


class PropertySearchView(TemplateView):
    """Страница поиска: витрина с фильтром и быстрыми ссылками в карточки."""

    template_name = 'propertysearch/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = RealtyOffer.objects.aggregate(
            total=Count('id'),
            min_price=Min('price'),
            max_price=Max('price'),
        )
        top_districts = list(
            RealtyOffer.objects.exclude(district__isnull=True)
            .exclude(district__exact='')
            .values('district')
            .annotate(total=Count('id'))
            .order_by('-total')[:6]
        )
        context['stats'] = stats
        context['top_districts'] = top_districts
        context['room_options'] = [1, 2, 3, 4, 5]
        return context


class PropertyComplexListView(TemplateView):
    """Публичная витрина ЖК в рамках поиска недвижимости."""

    template_name = 'propertysearch/complexes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cards = get_complex_cards()
        cards = sorted(cards, key=lambda c: c.get('units') or 0, reverse=True)
        context['cards'] = cards
        return context


class PropertyComplexDetailView(TemplateView):
    """Детальная публичная страница ЖК с предложениями квартир."""

    template_name = 'propertysearch/complex_detail.html'

    def get_context_data(self, slug, **kwargs):
        context = super().get_context_data(**kwargs)
        # Пытаемся найти ЖК по slug, а при неудаче - по нормализованному имени.
        complex_instance = (
            PartnerComplex.objects.filter(slug=slug, is_active=True).first()
            or PartnerComplex.objects.filter(normalized_name=slug.replace('-', ' ').lower(), is_active=True).first()
            or PartnerComplex.objects.filter(name__icontains=slug, is_active=True).first()
        )
        if not complex_instance:
            raise Http404("ЖК не найден")

        gallery = []
        try:
            gallery = load_gallery(slug)
        except Exception:
            gallery = []
        main_image = next((item for item in gallery if item.get("is_main")), None)
        hero_image = (main_image["url"] if main_image else None) or (gallery[0]["url"] if gallery else PLACEHOLDER_IMAGES[0])

        qs = RealtyOffer.objects.filter(building_name__icontains=complex_instance.name)
        rooms_list = [val.strip() for val in self.request.GET.getlist('rooms') if val.strip()]
        price_min = self.request.GET.get('price_min', '').strip()
        price_max = self.request.GET.get('price_max', '').strip()
        area_min = self.request.GET.get('area_min', '').strip()
        area_max = self.request.GET.get('area_max', '').strip()
        floor_min = self.request.GET.get('floor_min', '').strip()
        floor_max = self.request.GET.get('floor_max', '').strip()
        only_new = self.request.GET.get('only_new') == 'on'
        only_apartments = self.request.GET.get('only_apartments') == 'on'
        only_studio = self.request.GET.get('only_studio') == 'on'
        with_decoration = self.request.GET.get('with_decoration') == 'on'
        if rooms_list:
            valid_rooms = []
            for r in rooms_list:
                try:
                    valid_rooms.append(int(r))
                except ValueError:
                    continue
            if valid_rooms:
                qs = qs.filter(rooms__in=valid_rooms)
        if price_min:
            try:
                qs = qs.filter(price__gte=int(price_min))
            except ValueError:
                pass
        if price_max:
            try:
                qs = qs.filter(price__lte=int(price_max))
            except ValueError:
                pass
        if area_min:
            try:
                qs = qs.filter(area_total__gte=float(area_min))
            except ValueError:
                pass
        if area_max:
            try:
                qs = qs.filter(area_total__lte=float(area_max))
            except ValueError:
                pass
        if floor_min:
            try:
                qs = qs.filter(floor__gte=int(floor_min))
            except ValueError:
                pass
        if floor_max:
            try:
                qs = qs.filter(floor__lte=int(floor_max))
            except ValueError:
                pass
        if only_new:
            qs = qs.filter(is_new_flat=True)
        if only_apartments:
            qs = qs.filter(is_apartments=True)
        if only_studio:
            qs = qs.filter(is_studio=True)
        if with_decoration:
            qs = qs.exclude(decoration_type__isnull=True).exclude(decoration_type__exact='')
        sort = (self.request.GET.get('sort') or '').strip()
        allowed_sort = {
            'price_asc': 'price',
            'price_desc': '-price',
            'area_asc': 'area_total',
            'area_desc': '-area_total',
            'floor_asc': 'floor',
            'floor_desc': '-floor',
        }
        order_by = allowed_sort.get(sort) or 'price'
        offers = list(qs.order_by(order_by)[:50])

        # Дотягиваем недостающие поля (фото/планировки/доп. атрибуты) прямо из XML, как в /realestate/cards/.
        helper = RealEstateDashboardView()
        fallback = helper._load_fallback_data([offer.internal_id for offer in offers])
        for offer in offers:
            fb = fallback.get(offer.internal_id, {})
            offer.extra = fb
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
            xml_photos = fb.get('photos') or []
            model_photos = [p.strip() for p in (offer.photos or '').splitlines() if p.strip()]
            gallery = xml_photos or model_photos
            offer.gallery = gallery[:10]
            offer.hero_image = fb.get('plan_image') or fb.get('floor_image') or (gallery[0] if gallery else None)
            offer.room_spaces = fb.get('room_spaces') or []

        context.update({
            'complex': complex_instance,
            'gallery': gallery,
            'hero_image': hero_image,
            'offers': offers,
            'rooms_selected': [str(r) for r in rooms_list],
            'price_min': price_min,
            'price_max': price_max,
            'area_min': area_min,
            'area_max': area_max,
            'floor_min': floor_min,
            'floor_max': floor_max,
            'only_new': only_new,
            'only_apartments': only_apartments,
            'only_studio': only_studio,
            'with_decoration': with_decoration,
            'sort': sort or 'price_asc',
            'sort_options': [
                ('price_asc', 'Цена ↑'),
                ('price_desc', 'Цена ↓'),
                ('area_asc', 'Площадь ↑'),
                ('area_desc', 'Площадь ↓'),
                ('floor_asc', 'Этаж ↑'),
                ('floor_desc', 'Этаж ↓'),
            ],
        })
        return context
