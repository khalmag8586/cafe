import string, random
from django.db.models.signals import pre_save, post_migrate
from django.dispatch import receiver
from django.utils.text import slugify
from django.apps import apps
from django.db.models import Q
from django.http import JsonResponse
from urllib.parse import urljoin

from django.utils.translation import gettext_lazy as _
from rest_framework.views import APIView
from django.contrib.auth.models import Group, Permission
import os
from django.conf import settings
from escpos.printer import Network
from PIL import Image
from decimal import Decimal
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import textwrap


# def format_bill(order, payment, total_payment_amount, vat, save_as_pdf=False):
#     bill_text = []
#     bill_text.append("TAX INVOICE")
#     bill_text.append("Coffee Shop Co. L.L.C")
#     bill_text.append("Shop 1, Block A")
#     bill_text.append("Abraj Al Mamzar")
#     bill_text.append("Dubai, UAE")
#     bill_text.append("Ct: 0547606099 / 0559803445")
#     bill_text.append(f"TRN: 104340270800001")
#     bill_text.append("")
#     bill_text.append("Duplicate Bill")
#     bill_text.append("")

#     # Payment ID as Invoice No, Order ID as KOT No
#     bill_text.append(f"Invoice No: {payment}")  # Payment ID
#     bill_text.append(f"KOT No: {order.id}")  # Order ID
#     bill_text.append(f"Bill Date: {order.created_at.strftime('%d-%m-%Y')}")
#     bill_text.append(f"Check In: {order.created_at.strftime('%H-%M-%S')}")
#     bill_text.append("")
#     bill_text.append("Item - UOM    Qty    Price    Value")
#     bill_text.append("")

#     for item_data in order.order_items.all():
#         bill_text.append(f"{item_data.product.name} - Nos")
#         bill_text.append(
#             f"{item_data.quantity}    {item_data.product.price:.2f}    {item_data.quantity*item_data.product.price:.2f}"
#         )

#     # Get discount value (default to 0.00 if no discount is applied)
#     total_payment_amount = Decimal(total_payment_amount)
#     discount_value = order.discount.value if order.discount else Decimal("0.00")

#     # Append the calculated totals
#     bill_text.append("")
#     bill_text.append(f"SubTotal:    {total_payment_amount - discount_value:.2f}")
#     bill_text.append(f"Discount:    -{discount_value:.2f}")
#     bill_text.append(f"VAT (5%):    {vat:.2f}")
#     bill_text.append(f"Grand Total:   AED    {total_payment_amount:.2f}")
#     bill_text.append("")
#     bill_text.append("Thanks")
#     bill_text.append("Visit again")

#     # Join the bill text into a single string
#     formatted_bill_text = "\n".join(bill_text)

#     # Get the path to the logo file
#     logo_path = os.path.join(settings.MEDIA_ROOT, "default_photos", "logo.jpg")

#     # Define the PDF save path and public URL
#     pdf_url = None
#     if save_as_pdf:
#         filename = f"invoice_{order.id}.pdf"
#         pdf_path, pdf_url = save_bill_as_pdf(formatted_bill_text, filename, logo_path)

#     return (
#         formatted_bill_text,
#         logo_path,
#         pdf_url,
#     )  # ✅ Return public URL instead of local path


def format_bill(order, payment, total_payment_amount, vat, save_as_pdf=False):
    from apps.order.models import (
        Payment,
    )  # Replace with your actual app and model import
    import textwrap

    bill_text = []

    # Header
    bill_text.append("=" * 45)  # Header separator
    bill_text.append("        TAX INVOICE        ")
    bill_text.append("=" * 45)
    bill_text.append("  Coffee Shop Co. L.L.C  ")
    bill_text.append("     Shop 1, Block A     ")
    bill_text.append("     Abraj Al Mamzar     ")
    bill_text.append("       Dubai, UAE        ")
    bill_text.append("Ct: 0547606099 / 0559803445")
    bill_text.append(f"TRN: 104340270800001")
    bill_text.append("=" * 45)
    bill_text.append("      Duplicate Bill      ")
    bill_text.append("=" * 45)

    # Invoice and Order Details
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Invoice No: {payment}", f"Table: {order.table.table_number or 'N/A'}"
        )
    )
    bill_text.append(
        "{:<20} {:>20}".format(
            f"KOT No: {order.id}", f"No Of Pax: {order.number_of_pax or 'N/A'}"
        )
    )
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Bill Date: {order.created_at.strftime('%d-%m-%Y')}",
            f"Check Out: {order.check_out_time.strftime('%H:%M %S') if order.check_out_time else 'N/A'}",
        )
    )
    bill_text.append(f"Check In: {order.created_at.strftime('%H-%M-%S')}")
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Shift: {order.shift or 'N/A'}", f"Hall: {order.hall or 'N/A'}"
        )
    )
    bill_text.append("=" * 45)

    # Order Items (unchanged)
    for item_data in order.order_items.all():
        product_name = item_data.product.name
        quantity = item_data.quantity
        price = item_data.product.price
        total = quantity * price

        # Wrap product name to fit within 20 characters (adjustable)
        wrapped_product_name = textwrap.wrap(product_name, width=20)

        # Print the first line of the product name with the values
        bill_text.append(
            "{:<20} {:>6} {:<8.2f} {:<10.2f}".format(
                wrapped_product_name[0], quantity, price, total
            )
        )

        # Print any additional wrapped lines (without quantity, price, or total)
        for line in wrapped_product_name[1:]:
            bill_text.append("{:<20}".format(line))  # Just print the wrapped name

    bill_text.append("=" * 45)

    # Calculating totals (unchanged)
    total_payment_amount = Decimal(total_payment_amount)
    discount_value = order.discount.value if order.discount else Decimal("0.00")

    bill_text.append("")
    bill_text.append(f"SubTotal:       AED {total_payment_amount - discount_value:.2f}")
    bill_text.append(f"Discount:       AED -{discount_value:.2f}")
    bill_text.append(f"VAT (5%):       AED {vat:.2f}")
    bill_text.append("=" * 45)
    bill_text.append(f"Grand Total:    AED {total_payment_amount:.2f}")
    bill_text.append("=" * 45)

    # Collection Details
    try:
        payment_instance = Payment.objects.get(id=payment)  # Fetch the Payment instance
        bill_text.append("Collection Details:")
        bill_text.append("")
        bill_text.append(
            f"Payment Method: {payment_instance.payment_method}"
        )  # Assuming `method` is the field
        bill_text.append("=" * 45)
    except Payment.DoesNotExist:
        bill_text.append("Collection Details:")
        bill_text.append("Payment details not found.")
        bill_text.append("=" * 45)

    # Closing Note
    bill_text.append("")
    bill_text.append("    Thanks for your visit!    ")
    bill_text.append("        Visit Again!         ")
    bill_text.append("=" * 45)

    # Convert to formatted string
    formatted_bill_text = "\n".join(bill_text)

    # Get the path to the logo file
    logo_path = os.path.join(settings.MEDIA_ROOT, "default_photos", "logo.jpg")

    # Define the PDF save path and public URL
    pdf_url = None
    if save_as_pdf:
        filename = f"invoice_{order.id}.pdf"
        pdf_path, pdf_url = save_bill_as_pdf(formatted_bill_text, filename, logo_path)

    return (
        formatted_bill_text,
        logo_path,
        pdf_url,
    )  # ✅ Return public URL instead of local path


def save_bill_as_pdf(bill_text, filename, logo_path=None):
    """Save bill as a PDF file inside media/uploaded_photos/bills/."""

    # Define the target directory inside the media folder
    bills_dir = os.path.join(settings.MEDIA_ROOT, "uploads", "bills")
    os.makedirs(bills_dir, exist_ok=True)  # ✅ Ensure directory exists

    # Generate the full PDF file path
    pdf_path = os.path.join(bills_dir, filename)

    # Create PDF using ReportLab
    c = canvas.Canvas(pdf_path, pagesize=letter)
    y_position = 750  # Start writing from the top

    # Set smaller font size for the content
    c.setFont("Helvetica", 8)  # Reduce font size to 8 for smaller content

    # Add logo if available
    if logo_path and os.path.exists(logo_path):
        logo_width = 150
        logo_height = 75
        c.drawImage(
            logo_path,
            50,
            y_position - logo_height,
            width=logo_width,
            height=logo_height,
        )
        y_position -= logo_height + 10  # Adjust the y_position after the logo

    # Write each line of the bill with reduced line spacing
    for line in bill_text.split("\n"):
        c.drawString(50, y_position, line)
        y_position -= 15  # Reduced vertical spacing between lines

        # If space runs out, start a new page
        if y_position < 50:
            c.showPage()
            y_position = 750  # Reset the y position to the top of the new page

    c.save()
    print(f"Bill saved as PDF: {pdf_path}")

    # ✅ Generate public URL for the saved PDF
    pdf_relative_path = f"uploads/bills/{filename}"  # Relative path from MEDIA_URL
    pdf_url = urljoin(settings.MEDIA_URL, pdf_relative_path)

    return pdf_path, pdf_url  # ✅ Return both file path and public URL


def print_to_printer(printer_ip, bill_text, logo_path=None):
    try:
        printer = Network(printer_ip)

        # Print logo if provided
        if logo_path and os.path.exists(logo_path):
            logo = Image.open(logo_path).convert("L")  # Convert to grayscale
            logo = logo.resize(
                (512, int(logo.height * (512 / logo.width)))
            )  # Scale width to 512px
            printer.image(logo)
            printer.text("\n")  # Add a newline after the logo

        # Print bill text
        printer.text(bill_text + "\n")

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
