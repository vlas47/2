from django.db import migrations
from django.contrib.auth.hashers import make_password


ADMIN_GROUP = 'Администратор'
MANAGER_GROUP = 'Менеджер'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'


def create_roles_and_admin_user(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')

    admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    Group.objects.get_or_create(name=MANAGER_GROUP)

    admin_user, created = User.objects.get_or_create(
        username=ADMIN_USERNAME,
        defaults={
            'is_staff': True,
            'is_superuser': True,
            'password': make_password(ADMIN_PASSWORD),
        },
    )
    if not created:
        # ensure credentials if user already exists
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.password = make_password(ADMIN_PASSWORD)
        admin_user.save(update_fields=['is_staff', 'is_superuser', 'password'])

    admin_user.groups.add(admin_group)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_roles_and_admin_user, noop_reverse),
    ]
