from django.db import models
from django.utils.text import slugify


class PartnerComplex(models.Model):
    """Справочник жилых комплексов из Excel."""

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True)
    normalized_name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    apartments_count = models.PositiveIntegerField(default=0)
    district = models.CharField(max_length=150, blank=True, null=True)
    metro = models.CharField(max_length=150, blank=True, null=True)
    status = models.CharField(max_length=100, blank=True, null=True)
    price_label = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ('name',)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True)
            self.slug = base_slug or f'complex-{abs(hash(self.name)) % (10 ** 8):08d}'
        self.normalized_name = (self.name or '').strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
