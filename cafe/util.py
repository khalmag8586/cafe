import string, random
from django.db.models.signals import pre_save, post_migrate
from django.dispatch import receiver
from django.utils.text import slugify
from django.apps import apps
from django.db.models import Q
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from rest_framework.views import APIView
from django.contrib.auth.models import Group, Permission
import os
from django.conf import settings
from escpos.printer import Network
from PIL import Image
from decimal import Decimal
from collections import defaultdict


def split_bill(order, pax_items):
    """
    Split the bill for an order based on which items and quantities each pax has paid for.

    :param order: The Order instance.
    :param pax_items: A dictionary where keys are pax numbers and values are dictionaries
                      of item IDs and quantities they are paying for.
                      Example: {1: {"item_id1": 2, "item_id2": 1}, 2: {"item_id1": 1}}
    :return: A dictionary with pax numbers as keys and their respective bills as values.
    """
    from apps.order.models import OrderItems

    bills = {}
    item_quantities = defaultdict(int)  # Track remaining quantities for each item

    # Initialize item quantities
    for item in order.order_items.all():
        item_quantities[item.id] = item.quantity

    for pax, item_quantities_dict in pax_items.items():
        pax_bill = {
            "items": [],
            "total": Decimal("0.00"),
        }

        for item_id, quantity in item_quantities_dict.items():
            try:
                item = order.order_items.get(id=item_id)
                if item_quantities[item.id] < quantity:
                    raise ValueError(
                        f"Pax {pax} is trying to pay for more quantity than available for item {item.id}."
                    )

                # Calculate the subtotal for the paid quantity
                sub_total = (item.product.price * Decimal(quantity)).quantize(
                    Decimal("0.00")
                )
                pax_bill["items"].append(
                    {
                        "id": item.id,
                        "product_name": item.product.name,
                        "quantity": quantity,
                        "sub_total": sub_total,
                    }
                )
                pax_bill["total"] += sub_total

                # Update the remaining quantity for the item
                item_quantities[item.id] -= quantity

                # Mark the item as paid if the entire quantity is paid
                if item_quantities[item.id] == 0:
                    item.is_paid = True
                    item.paid_by = pax
                    item.save()

            except OrderItems.DoesNotExist:
                raise ValueError(f"Item with ID {item_id} does not exist in the order.")

        bills[pax] = pax_bill

    # Check if all items in the order are paid
    if all(quantity == 0 for quantity in item_quantities.values()):
        order.is_paid = True
        order.save()

    return bills


def format_bill(order, payment, total_payment_amount, vat):
    bill_text = []
    bill_text.append("TAX INVOICE")
    bill_text.append("Coffee Shop Co. L.L.C")
    bill_text.append("Shop 1, Block A")
    bill_text.append("Abraj Al Mamzar")
    bill_text.append("Dubai, UAE")
    bill_text.append("Ct: 0547606099 / 0559803445")
    bill_text.append(f"TRN: 104340270800001")
    bill_text.append("")
    bill_text.append("Duplicate Bill")
    bill_text.append("")

    # Payment ID as Invoice No, Order ID as KOT No
    bill_text.append(f"Invoice No: {payment}")  # Payment ID
    bill_text.append(f"KOT No: {order.id}")  # Order ID
    bill_text.append(f"Bill Date: {order.created_at.strftime('%d-%m-%Y')}")
    bill_text.append(f"Check In: {order.created_at.strftime('%H-%M-%S')}")

    bill_text.append("")
    bill_text.append("Item - UOM    Qty    Price    Value")
    bill_text.append("")

    for item_data in order.order_items.all():
        bill_text.append(f"{item_data.product.name} - Nos")
        bill_text.append(
            f"{item_data.quantity}    {item_data.product.price:.2f}    {item_data.sub_total:.2f}"
        )

    # Append the calculated totals
    bill_text.append("")
    bill_text.append(f"SubTotal:    {total_payment_amount- vat:.2f}")
    bill_text.append(f"VAT (5%):    {vat:.2f}")
    bill_text.append(f"Grand Total:   AED    {(total_payment_amount):.2f}")
    bill_text.append("")
    bill_text.append("Thanks")
    bill_text.append("Visit again")

    # Join the bill text into a single string
    formatted_bill_text = "\n".join(bill_text)

    # Get the path to the logo file
    logo_path = os.path.join(settings.MEDIA_ROOT, "default_photos", "logo.jpg")

    # Check if the logo file exists
    if not os.path.exists(logo_path):
        logo_path = None  # If the logo doesn't exist, set logo_path to None

    return formatted_bill_text, logo_path


def format_barista_order(order):
    drink_items = order.order_items.filter(product__category__name="Drinks")
    if not drink_items.exists():
        return None

    drink_text = ["Drinks Order:"]
    drink_text.append(f"Order No: {order.id}")
    drink_text.append("")
    for item in drink_items:
        drink_text.append(f"{item.product.name} - {item.quantity} Nos")
    return "\n".join(drink_text)


def format_shisha_order(order):
    shisha_items = order.order_items.filter(product__category__name="Shisha")
    if not shisha_items.exists():
        return None

    shisha_text = ["Shisha Order:"]
    shisha_text.append(f"Order No: {order.id}")
    shisha_text.append("")
    for item in shisha_items:
        shisha_text.append(f"{item.product.name} - {item.quantity} Nos")
    return "\n".join(shisha_text)


def print_to_printer(printer_ip, bill_text, logo_path=None):
    try:
        printer = Network(printer_ip)

        # Print logo if provided
        if logo_path and os.path.exists(logo_path):
            logo = Image.open(logo_path)
            printer.image(logo)
            printer.text("\n")  # Add a newline after the logo

        # Print bill text
        for line in bill_text.split("\n"):
            printer.text(line + "\n")

        # Cut the paper
        printer.cut()

        print(f"Print job sent to printer at {printer_ip}")
    except Exception as e:
        print(f"Failed to print to {printer_ip}: {e}")


########################################################
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
        field_name = request.GET.get("field")
        field_value = request.GET.get("value")

        if not field_name or not field_value:
            return JsonResponse(
                {
                    "detail": _(
                        "Field name and value are required in the query parameters."
                    )
                },
                status=400,
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
            message = _(
                "The value '{}' already exists in the following models: {}"
            ).format(field_value, ", ".join(existing_models))
            return JsonResponse({"is_exist": True, "detail": message}, status=200)
        else:
            message = _("The value '{}' does not exist in any model.").format(
                field_value
            )
            return JsonResponse({"is_exist": False, "detail": message}, status=200)


@receiver(post_migrate)
def create_initial_groups(sender, **kwargs):
    if sender.name == "user":
        # Create or get the 'admins' group
        admin_group, created = Group.objects.get_or_create(name="admins")

        # Assign all permissions to the 'admins' group
        all_permissions = Permission.objects.all()
        admin_group.permissions.set(all_permissions)

        # Create or get the 'normal' group
        normal_group, created = Group.objects.get_or_create(name="normal")

        # Assign view permissions to the 'normal' group
        # Assuming 'view' permissions are represented by the 'view' codename
        view_permissions = Permission.objects.filter(codename__startswith="view")
        normal_group.permissions.set(view_permissions)
