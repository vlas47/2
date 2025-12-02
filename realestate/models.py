from django.db import models


class RealtyOffer(models.Model):
    """Основная запись о предложении недвижимости из фида Setl."""

    internal_id = models.CharField(max_length=64, unique=True)
    case_id = models.CharField(max_length=64, blank=True, null=True)
    deal_type = models.CharField(max_length=50, blank=True, null=True)
    property_type = models.CharField(max_length=50, blank=True, null=True)
    category = models.CharField(max_length=50, blank=True, null=True)
    deal_status = models.CharField(max_length=100, blank=True, null=True)
    deal_state = models.CharField(max_length=100, blank=True, null=True)
    creation_date = models.DateTimeField(blank=True, null=True)
    last_update_date = models.DateTimeField(blank=True, null=True)

    country = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    locality_name = models.CharField(max_length=150, blank=True, null=True)
    sub_locality_name = models.CharField(max_length=150, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    metro_name = models.CharField(max_length=100, blank=True, null=True)
    metro_time_on_foot = models.PositiveIntegerField(blank=True, null=True)
    metro_time_on_transport = models.PositiveIntegerField(blank=True, null=True)

    price = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    price_base = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    price_cost = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)

    area_total = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    area_living = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    area_kitchen = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    area_lot = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    area_balcony = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    rooms = models.PositiveIntegerField(blank=True, null=True)
    floor = models.IntegerField(blank=True, null=True)
    floors_total = models.IntegerField(blank=True, null=True)
    ceiling_height = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    is_new_flat = models.BooleanField(default=False)
    is_apartments = models.BooleanField(default=False)
    is_studio = models.BooleanField(default=False)

    building_id = models.CharField(max_length=64, blank=True, null=True)
    building_name = models.CharField(max_length=150, blank=True, null=True)
    building_state = models.CharField(max_length=100, blank=True, null=True)
    building_phase = models.CharField(max_length=100, blank=True, null=True)
    building_type = models.CharField(max_length=100, blank=True, null=True)
    building_section = models.CharField(max_length=100, blank=True, null=True)
    building_material = models.CharField(max_length=100, blank=True, null=True)
    building_year = models.CharField(max_length=50, blank=True, null=True)
    brand = models.CharField(max_length=100, blank=True, null=True)

    decoration_type = models.CharField(max_length=100, blank=True, null=True)
    number_flat = models.CharField(max_length=50, blank=True, null=True)
    entrance = models.CharField(max_length=50, blank=True, null=True)
    section = models.CharField(max_length=50, blank=True, null=True)

    photos = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    reserve_char_1 = models.CharField(max_length=200, blank=True, null=True)
    reserve_char_2 = models.CharField(max_length=200, blank=True, null=True)
    reserve_char_3 = models.CharField(max_length=200, blank=True, null=True)
    reserve_char_4 = models.CharField(max_length=200, blank=True, null=True)
    reserve_char_5 = models.CharField(max_length=200, blank=True, null=True)
    reserve_text_1 = models.TextField(blank=True, null=True)
    reserve_text_2 = models.TextField(blank=True, null=True)
    reserve_text_3 = models.TextField(blank=True, null=True)
    reserve_text_4 = models.TextField(blank=True, null=True)
    reserve_text_5 = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ('-last_update_date', 'internal_id')

    def __str__(self) -> str:
        return f'{self.internal_id} — {self.address or self.building_name or "объект"}'

# Create your models here.
