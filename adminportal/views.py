from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView

from .services import (
    get_consult_steps,
    get_dashboard_cards,
    get_partner_intro,
    get_partner_points,
)


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Внутренний раздел для менеджеров."""

    template_name = 'adminportal/dashboard.html'
    login_url = reverse_lazy('adminportal:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dashboard_cards'] = get_dashboard_cards()
        context['partner_intro'] = get_partner_intro()
        context['partner_points'] = get_partner_points()
        context['steps'] = get_consult_steps()
        return context

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.groups.filter(name__in=['Администратор', 'Менеджер']).exists()


class StaffLoginView(LoginView):
    template_name = 'adminportal/login.html'

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        user = self.request.user
        if user.is_superuser or user.groups.filter(name='Администратор').exists():
            return reverse('adminportal:dashboard')
        return reverse('realestate:dashboard')
