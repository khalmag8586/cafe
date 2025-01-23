import string, random
from django.db.models.signals import pre_save,post_migrate
from django.dispatch import receiver
from django.utils.text import slugify
from django.apps import apps
from django.db.models import Q
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from rest_framework.views import APIView
from django.contrib.auth.models import Group, Permission


def random_string_generator(size=10, chars=string.ascii_lowercase + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


def unique_slug_generator(instance, new_slug=None):
    if new_slug is not None:
        slug = new_slug
    else:
        slug = slugify(instance.name)
    Klass = instance.__class__
    max_length = Klass._meta.get_field("slug").max_length
    slug = slug[:max_length]
    qs_exists = Klass.objects.filter(slug=slug).exists()

    if qs_exists:
        new_slug = "{slug}-{randstr}".format(
            slug=slug[: max_length - 5], randstr=random_string_generator(size=4)
        )

        return unique_slug_generator(instance, new_slug=new_slug)
    return slug


class CheckFieldValueExistenceView(APIView):
    def get(self, request):
        field_name = request.GET.get('field')
        field_value = request.GET.get('value')

        if not field_name or not field_value:
            return JsonResponse(
                {"detail": _("Field name and value are required in the query parameters.")},
                status=400
            )

        app_models = apps.get_models()

        # List to store model names where the field exists
        existing_models = []

        # Iterate through all models and check if the field exists
        for model in app_models:
            if hasattr(model, field_name):
                # Use Q objects to handle fields with the same name
                filter_query = Q(**{field_name: field_value})
                exists = model.objects.filter(filter_query).exists()
                if exists:
                    existing_models.append(model.__name__)

        if existing_models:
            message = _("The value '{}' already exists in the following models: {}").format(
                field_value, ', '.join(existing_models)
            )
            return JsonResponse(
                {"is_exist": True, "detail": message},
                status=200
            )
        else:
            message = _("The value '{}' does not exist in any model.").format(field_value)
            return JsonResponse(
                {"is_exist": False, "detail": message},
                status=200
            )


@receiver(post_migrate)
def create_initial_groups(sender, **kwargs):
    if sender.name == 'user':
        # Create or get the 'admins' group
        admin_group, created = Group.objects.get_or_create(name='admins')

        # Assign all permissions to the 'admins' group
        all_permissions = Permission.objects.all()
        admin_group.permissions.set(all_permissions)

        # Create or get the 'normal' group
        normal_group, created = Group.objects.get_or_create(name='normal')

        # Assign view permissions to the 'normal' group
        # Assuming 'view' permissions are represented by the 'view' codename
        view_permissions = Permission.objects.filter(codename__startswith='view')
        normal_group.permissions.set(view_permissions)