import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify


def slugify_name(name: str) -> str:
    slug = slugify(name or '', allow_unicode=True)
    if slug:
        return slug
    fallback = hashlib.md5((name or '').encode('utf-8')).hexdigest()[:8]
    return f'complex-{fallback}'


_gallery_root = getattr(settings, 'COMPLEXES_GALLERY_ROOT', None)
if _gallery_root:
    GALLERY_ROOT = Path(_gallery_root)
else:
    GALLERY_ROOT = settings.BASE_DIR / 'static' / 'complexes_photos'


def gallery_dir(slug: str) -> Path:
    root = globals().get('GALLERY_ROOT')
    if root is None:
        override = getattr(settings, 'COMPLEXES_GALLERY_ROOT', None)
        if override:
            root = Path(override)
        else:
            root = settings.BASE_DIR / 'static' / 'complexes_photos'
        GALLERY_ROOT = root
    return root / slug


def gallery_file_path(slug: str, filename: str) -> Path:
    return gallery_dir(slug) / filename


def gallery_json_path(slug: str) -> Path:
    return gallery_dir(slug) / 'gallery.json'


def load_gallery_raw(slug: str) -> list[dict]:
    path = gallery_json_path(slug)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []
    return data


def save_gallery_raw(slug: str, entries: list[dict]) -> None:
    path = gallery_json_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    simple = [{'file': entry['file'], 'is_main': entry.get('is_main', False)} for entry in entries]
    path.write_text(json.dumps(simple, ensure_ascii=False), encoding='utf-8')


def load_gallery(slug: str) -> list[dict]:
    entries = load_gallery_raw(slug)
    for entry in entries:
        try:
            entry['url'] = reverse('complexes:photo', args=[slug, entry['file']])
        except Exception:
            entry['url'] = f'/static/complexes_photos/{slug}/{entry["file"]}'
    return entries


def normalize_complex_name(value: str) -> str:
    if not value:
        return ''
    return value.strip().lower()


def append_gallery_entries(slug: str, files: list[str], main_index: int) -> list[dict]:
    entries = load_gallery_raw(slug)
    for entry in entries:
        entry['is_main'] = False
    for idx, file in enumerate(files):
        entries.append({'file': file, 'is_main': idx == main_index})
    save_gallery_raw(slug, entries)
    return entries


def remove_gallery_entry(slug: str, filename: str) -> list[dict]:
    entries = load_gallery_raw(slug)
    filtered = [entry for entry in entries if entry['file'] != filename]
    save_gallery_raw(slug, filtered)
    path = gallery_file_path(slug, filename)
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass
    return filtered


def set_gallery_main(slug: str, filename: str) -> list[dict]:
    entries = load_gallery_raw(slug)
    found = False
    for entry in entries:
        is_target = entry['file'] == filename
        entry['is_main'] = is_target
        if is_target:
            found = True
    if not found and entries:
        entries[0]['is_main'] = True
    save_gallery_raw(slug, entries)
    return entries
