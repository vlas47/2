from django.views.generic import TemplateView

from .services import (
    get_countryside_benefits,
    get_countryside_programs,
    get_countryside_text,
)


class CountrysideView(TemplateView):
    """Страница с загородными программами."""

    template_name = 'countryside/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['countryside_text'] = get_countryside_text()
        context['countryside_programs'] = get_countryside_programs()
        context['countryside_benefits'] = get_countryside_benefits()
        return context
