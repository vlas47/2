from django.views.generic import TemplateView

from .services import get_benefits, get_focus_blocks, get_highlights, get_workflow


class NewBuildingsView(TemplateView):
    """Раздел с витриной новостроек."""

    template_name = 'newbuildings/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['benefits'] = get_benefits()
        context['workflow'] = get_workflow()
        context['focus_blocks'] = get_focus_blocks()
        context['highlights'] = get_highlights()
        return context
