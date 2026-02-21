import json
from uuid import uuid4
import logging
import mimetypes
import re

from PIL import Image
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from .forms import ComplexPhotoUploadForm
from .models import PartnerComplex
from .services import (
    get_complex_cards,
    get_complex_summary,
    get_active_complexes,
    refresh_complex_data_from_offers,
)
from .utils import (
    append_gallery_entries,
    gallery_dir,
    gallery_file_path,
    load_gallery,
    remove_gallery_entry,
    set_gallery_main,
    slugify_name,
)

logger = logging.getLogger(__name__)


class ComplexListView(TemplateView):
    """Отображает карточки жилищных комплексов."""

    template_name = 'complexes/index.html'
    SORTING_OPTIONS = [
        ('name', 'По названию (А→Я)'),
        ('units_desc', 'По количеству квартир'),
        ('price_asc', 'Цена: от дешёвых'),
        ('price_desc', 'Цена: от дорогих'),
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_complexes = get_active_complexes()
        selected_slug = self.request.GET.get('complex', '').strip()
        district_query = self.request.GET.get('district', '').strip().lower()
        metro_query = self.request.GET.get('metro', '').strip().lower()
        selected_sort = self.request.GET.get('sort', 'name').strip() or 'name'
        filtered = self._filter_complexes(all_complexes, selected_slug, district_query, metro_query)
        ordered = self._sort_complexes(filtered, selected_sort)
        context['complexes'] = get_complex_cards(ordered)
        context['summary'] = get_complex_summary(filtered if (selected_slug or district_query or metro_query) else all_complexes)
        context['complex_choices'] = [(complex_instance.slug, complex_instance.name) for complex_instance in all_complexes]
        context['selected_complex'] = selected_slug
        context['selected_district'] = district_query
        context['selected_metro'] = metro_query
        context['sorting_options'] = self.SORTING_OPTIONS
        context['selected_sort'] = selected_sort
        context['has_filters'] = bool(
            selected_slug or district_query or metro_query or (selected_sort and selected_sort != 'name')
        )
        return context

    def _filter_complexes(self, complexes, slug, district_query, metro_query):
        if not slug:
            filtered = complexes
        else:
            filtered = [complex_instance for complex_instance in complexes if complex_instance.slug == slug]
        if district_query:
            filtered = [
                complex_instance for complex_instance in filtered
                if district_query in (complex_instance.district or '').lower()
            ]
        if metro_query:
            filtered = [
                complex_instance for complex_instance in filtered
                if metro_query in (complex_instance.metro or '').lower()
            ]
        return filtered

    def _price_to_number(self, label):
        if not label:
            return None
        digits = re.sub(r'\D', '', label)
        return int(digits) if digits else None

    def _sort_complexes(self, complexes, mode):
        if mode == 'units_desc':
            return sorted(complexes, key=lambda item: item.apartments_count or 0, reverse=True)
        if mode == 'price_asc':
            return sorted(complexes, key=lambda item: self._price_to_number(item.price_label) or float('inf'))
        if mode == 'price_desc':
            return sorted(complexes, key=lambda item: self._price_to_number(item.price_label) or 0, reverse=True)
        return sorted(complexes, key=lambda item: item.name.lower())


class ComplexRefreshDataView(View):
    """Пересчитывает агрегаты по ЖК на основе базы realestate."""

    def post(self, request):
        stats = refresh_complex_data_from_offers()
        updated = stats.get('updated', 0)
        if updated:
            without = stats.get('without_offers', 0)
            messages.success(
                request,
                f'Обновлено {updated} ЖК. Без предложений в базе: {without}.'
            )
        else:
            messages.info(request, 'Нет актуальных данных для обновления.')
        return redirect('complexes:index')


class ComplexFieldUpdateView(View):
    """Обновляет отдельное поле PartnerComplex без перезагрузки."""

    ALLOWED_FIELDS = {'district', 'metro', 'description'}
    DISPLAY_DEFAULTS = {
        'district': 'Район уточняется',
        'metro': 'Метро уточняется',
        'description': 'Описание уточняется',
    }

    def post(self, request, slug):
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'success': False, 'message': 'Некорректный формат данных.'}, status=400)
        field = (payload.get('field') or '').strip()
        if field not in self.ALLOWED_FIELDS:
            return JsonResponse({'success': False, 'message': 'Поле недоступно для редактирования.'}, status=400)
        value = (payload.get('value') or '').strip()
        try:
            complex_instance = PartnerComplex.objects.get(slug=slug, is_active=True)
        except PartnerComplex.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'ЖК не найден.'}, status=404)
        setattr(complex_instance, field, value or None)
        complex_instance.save(update_fields=[field, 'updated_at'])
        display_value = value or self.DISPLAY_DEFAULTS.get(field, '')
        return JsonResponse({
            'success': True,
            'field': field,
            'value': value,
            'display_value': display_value,
        })


class ComplexPhotoFileView(View):
    """Отдаёт отдельное фото из каталога ЖК."""

    def get(self, request, slug: str, filename: str):
        file_path = gallery_dir(slug) / filename
        if not file_path.exists() or not file_path.is_file():
            raise Http404('Фото не найдено.')
        content_type, _ = mimetypes.guess_type(file_path.as_posix())
        response = FileResponse(file_path.open('rb'), content_type=content_type or 'application/octet-stream')
        response['Cache-Control'] = 'public, max-age=86400'
        return response


class ComplexPhotoDeleteView(View):
    """Удаляет фото из галереи."""

    def post(self, request, slug: str, filename: str):
        if not slug or not filename:
            return JsonResponse({'success': False, 'message': 'Не указан файл.'}, status=400)
        remove_gallery_entry(slug, filename)
        gallery = load_gallery(slug)
        return JsonResponse({
            'success': True,
            'message': 'Фото удалено.',
            'files_on_server': gallery,
            'slug': slug,
        })


class ComplexPhotoSetMainView(View):
    """Устанавливает главное фото в галерее."""

    def post(self, request, slug: str, filename: str):
        if not slug or not filename:
            return JsonResponse({'success': False, 'message': 'Не указан файл.'}, status=400)
        set_gallery_main(slug, filename)
        gallery = load_gallery(slug)
        return JsonResponse({
            'success': True,
            'message': 'Главное фото обновлено.',
            'files_on_server': gallery,
            'slug': slug,
        })


class ComplexPhotoUploadView(View):
    """Обрабатывает загрузку фото без зависимости от FormView."""

    success_url = reverse_lazy('complexes:index')

    def is_ajax(self, request) -> bool:
        return request.headers.get('x-requested-with') == 'XMLHttpRequest'

    def json_response(
        self,
        message: str,
        success: bool = False,
        errors: dict | None = None,
        status: int = 400,
        logs: list[str] | None = None,
        files_on_server: list[dict] | None = None,
        slug: str | None = None,
    ):
        payload = {'success': success, 'message': message}
        if errors:
            payload['errors'] = errors
        if logs:
            payload['logs'] = logs
        if files_on_server is not None:
            payload['files_on_server'] = files_on_server
        if slug:
            payload['slug'] = slug
        return JsonResponse(payload, status=status)

    def log_invalid(self, form, request):
        file_details = {
            key: [file.name for file in files]
            for key, files in request.FILES.lists()
        }
        logger.warning(
            'ComplexPhotoUploadForm invalid: %s | POST=%s | FILES=%s | META=%s',
            form.errors,
            dict(request.POST),
            file_details,
            {
                'CONTENT_TYPE': request.META.get('CONTENT_TYPE'),
                'CONTENT_LENGTH': request.META.get('CONTENT_LENGTH'),
                'HTTP_CONTENT_TYPE': request.META.get('HTTP_CONTENT_TYPE'),
            },
        )

    def handle_files(self, request, form):
        files = request.FILES.getlist('files')
        logs: list[str] = ['Проверка файлов и подготовка к обработке.']
        if not files:
            if self.is_ajax(request):
                return self.json_response(
                    'Загрузите хотя бы одно фото.',
                    errors={'files': ['Загрузите хотя бы одно фото.']},
                    logs=logs,
                )
            messages.error(request, 'Загрузите хотя бы одно фото.')
            return redirect(self.success_url)
        logs.append(f'Найдено {len(files)} файлов для загрузки.')

        slug = slugify_name(form.cleaned_data['complex_name'])
        target_dir = gallery_dir(slug)
        target_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS
        for img_file in files:
            try:
                image = Image.open(img_file)
            except Exception:
                logs.append(f'Не удалось открыть файл {img_file.name}.')
                continue
            image = image.convert('RGB')
            image.thumbnail((500, 500), resample)
            filename = f'{uuid4().hex}.jpg'
            image.save(target_dir / filename, format='JPEG', quality=85)
            saved.append(filename)
            logs.append(f'Сохранено {img_file.name} → {filename} ({image.width}×{image.height}).')

        if not saved:
            if self.is_ajax(request):
                return self.json_response(
                    'Не удалось обработать ни один файл.',
                    errors={'files': ['Не удалось обработать ни один файл.']},
                    logs=logs,
                )
            messages.error(request, 'Не удалось обработать ни один файл.')
            return redirect(self.success_url)

        main_index = form.cleaned_data.get('main_index') or 0
        try:
            main_index = int(main_index)
        except Exception:
            main_index = 0
        main_index = max(0, min(main_index, len(saved) - 1))
        append_gallery_entries(slug, saved, main_index)
        messages.success(request, 'Фото загружены и сохранены.')
        logs.append(f'В галерее «{slug}» сохранено {len(saved)} новых файлов.')
        gallery = load_gallery(slug)
        files_on_server = [
            {'name': entry['file'], 'url': entry['url'], 'is_main': entry.get('is_main', False)}
            for entry in gallery
        ]
        if self.is_ajax(request):
            return self.json_response(
                'Фото загружены и обработаны. Обновите страницу, чтобы видеть галерею.',
                success=True,
                status=200,
                logs=logs,
                files_on_server=files_on_server,
                slug=slug,
            )
        return redirect(self.success_url)

    def post(self, request):
        form = ComplexPhotoUploadForm(request.POST)
        if not form.is_valid():
            self.log_invalid(form, request)
            errors = {field: [str(err) for err in errs] for field, errs in form.errors.items()}
            if self.is_ajax(request):
                return self.json_response('Не удалось загрузить фото — проверьте форму.', errors=errors)
            for field_errors in errors.values():
                for error in field_errors:
                    messages.error(request, error)
            return redirect(self.success_url)

        return self.handle_files(request, form)
