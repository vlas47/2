from django.views.generic import TemplateView

from .services import (
    get_consult_steps,
    get_dashboard_cards,
    get_partner_intro,
    get_partner_points,
)


class AdminDashboardView(TemplateView):
    """Внутренний раздел для менеджеров."""

    template_name = 'adminportal/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dashboard_cards'] = get_dashboard_cards()
        context['partner_intro'] = get_partner_intro()
        context['partner_points'] = get_partner_points()
        context['steps'] = get_consult_steps()
        return context
