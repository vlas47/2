from django.views.generic import TemplateView

from .services import get_secondary_intro, get_secondary_note, get_secondary_points


class SecondaryView(TemplateView):
    """Страница с программами вторички и trade-in."""

    template_name = 'secondary/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['secondary_intro'] = get_secondary_intro()
        context['secondary_points'] = get_secondary_points()
        context['secondary_note'] = get_secondary_note()
        return context
