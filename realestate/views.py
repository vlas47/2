from django.db.models import Q
from django.views.generic import TemplateView

from .models import RealtyOffer


class RealEstateDashboardView(TemplateView):
    """Простая служебная страница с краткой статистикой базы предложений."""

    template_name = 'realestate/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self._build_queryset()
        context['offers_total'] = RealtyOffer.objects.count()
        context['filtered_total'] = queryset.count()
        context['offers'] = queryset[:200]
        context['filters'] = self.request.GET
        context['order'] = self.request.GET.get('order', '-last_update_date')
        base_query = self.request.GET.copy()
        base_query.pop('order', None)
        context['base_query'] = base_query.urlencode()
        context['sort_options'] = {
            '-last_update_date': 'По обновлению ↓',
            'last_update_date': 'По обновлению ↑',
            'price': 'Цена ↑',
            '-price': 'Цена ↓',
            'rooms': 'Комнаты ↑',
            '-rooms': 'Комнаты ↓',
            'area': 'Площадь ↑',
            '-area': 'Площадь ↓',
        }
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
        rooms = params.get('rooms')
        if rooms and rooms.isdigit():
            qs = qs.filter(rooms=int(rooms))
        prop_type = params.get('type')
        if prop_type:
            qs = qs.filter(property_type__icontains=prop_type)
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
