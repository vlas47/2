from django.conf import settings
from django.http import HttpResponse
from django.views import View


class LandingView(View):
    """Отдаёт HTML из файла soyz.html (экспорт с Tilda)."""

    source_path = settings.BASE_DIR / 'soyz.html'

    def get(self, request, *args, **kwargs):
        content = self.source_path.read_text(encoding='utf-8')
        return HttpResponse(content)
