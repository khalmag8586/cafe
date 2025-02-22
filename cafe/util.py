import string, random
from django.db.models.signals import pre_save, post_migrate
from django.db.models import Sum
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
import random
from django.utils.timezone import now
from datetime import datetime
from collections import defaultdict
from arabic_reshaper import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


def format_arabic_text(text):
    """Reshape and reorder Arabic text for proper rendering."""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text


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
    bill_text.append("      Checkout Bill      ")
    bill_text.append("=" * 45)

    # Invoice and Order Details
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Invoice No: {payment}", f"Table: {order.table.table_number or 'N/A'}"
        )
    )
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Order No: {order.id}", f"No Of Pax: {order.number_of_pax or 'N/A'}"
        )
    )
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Bill Date: {order.created_at.strftime('%d-%m-%Y')}",
            f"Check Out: {order.check_out_time.strftime('%H:%M %S') if order.check_out_time else 'N/A'}",
        )
    )
    bill_text.append(f"Check In: {order.created_at.strftime('%H:%M:%S')}")
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Shift: {order.shift or 'N/A'}", f"Hall: {order.hall or 'N/A'}"
        )
    )
    bill_text.append("=" * 45)
    # Table Header
    bill_text.append(
        "{:<20} {:>6} {:>8} {:>10}".format("Item - UOM", "Qty", "Price", "Value")
    )
    bill_text.append("-" * 45)
    # Order Items (unchanged)
    for item_data in order.order_items.filter(remaining_quantity__gt=0):
        product_name = item_data.product.name
        product_name_ar = item_data.product.name_ar
        quantity = item_data.remaining_quantity
        price = item_data.product.price
        total = quantity * price

        # Wrap product name to fit within 20 characters (adjustable)
        wrapped_product_name = textwrap.wrap(product_name, width=20)
        wrapped_product_name_ar = textwrap.wrap(product_name_ar, width=20)

        # Print the first line of the product name with the values
        bill_text.append(
            "{:<20} {:>6} {:<8.2f} {:<10.2f}".format(
                wrapped_product_name[0], quantity, price, total
            )
        )

        # Print any additional wrapped lines (without quantity, price, or total)
        for line in wrapped_product_name[1:]:
            bill_text.append("{:<20}".format(line))  # Just print the wrapped name
        # Print the Arabic product name below the English name
        for line in wrapped_product_name_ar:
            bill_text.append("{:<20}".format(line))  # Align Arabic name
    bill_text.append("=" * 45)

    # Calculating totals (unchanged)
    total_payment_amount = Decimal(total_payment_amount)
    discount_value = order.discount.value if order.discount else Decimal("0.00")

    bill_text.append("")
    bill_text.append(f"SubTotal:       AED {order.final_total:.2f}")
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
        if payment:
            filename = f"invoice_{payment}.pdf"
        else:
            random_number = random.randint(
                100000, 999999
            )  # Generate a 6-digit random number
            filename = f"invoice_order_{order.id}_{random_number}.pdf"
        pdf_path, pdf_url = save_bill_as_pdf(formatted_bill_text, filename, logo_path)

    return (
        formatted_bill_text,
        logo_path,
        pdf_url,
    )  #  Return public URL instead of local path


def split_format_bill(
    order, payment, selected_items, total_payment_amount, vat, save_as_pdf=False
):
    import textwrap
    from apps.order.models import Payment

    bill_text = []

    # Header
    bill_text.append("=" * 45)
    bill_text.append("        TAX INVOICE        ")
    bill_text.append("=" * 45)
    bill_text.append("  Coffee Shop Co. L.L.C  ")
    bill_text.append("     Shop 1, Block A     ")
    bill_text.append("     Abraj Al Mamzar     ")
    bill_text.append("       Dubai, UAE        ")
    bill_text.append("Ct: 0547606099 / 0559803445")
    bill_text.append("TRN: 104340270800001")
    bill_text.append("=" * 45)
    bill_text.append("      Split Bill      ")
    bill_text.append("=" * 45)

    # Invoice and Order Details
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Invoice No: {payment}", f"Table: {order.table.table_number or 'N/A'}"
        )
    )
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Order No: {order.id}", f"No Of Pax: {order.number_of_pax or 'N/A'}"
        )
    )
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Bill Date: {order.created_at.strftime('%d-%m-%Y')}",
            f"Check Out: {order.check_out_time.strftime('%H:%M:%S') if order.check_out_time else 'N/A'}",
        )
    )
    bill_text.append(f"Check In: {order.created_at.strftime('%H:%M:%S')}")
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Shift: {order.shift or 'N/A'}", f"Hall: {order.hall or 'N/A'}"
        )
    )
    bill_text.append("=" * 45)

    # Table Header
    bill_text.append(
        "{:<20} {:>6} {:>8} {:>10}".format("Item - UOM", "Qty", "Price", "Value")
    )
    bill_text.append("-" * 45)

    # Order Items (only selected ones)
    for item_data in selected_items:
        product_name = item_data["product"].name
        product_name_ar = item_data["product"].name_ar
        quantity = item_data["quantity"]
        price = item_data["product"].price
        total = quantity * price

        # Wrap product name to fit within 20 characters
        wrapped_product_name = textwrap.wrap(product_name, width=20)
        wrapped_product_name_ar = textwrap.wrap(product_name_ar, width=20)

        # Print the first line of the product name with values
        bill_text.append(
            "{:<20} {:>6} {:<8.2f} {:<10.2f}".format(
                wrapped_product_name[0], quantity, price, total
            )
        )

        # Print any additional wrapped lines (without quantity, price, or total)
        for line in wrapped_product_name[1:]:
            bill_text.append("{:<20}".format(line))
        # Print the Arabic product name below the English name
        for line in wrapped_product_name_ar:
            bill_text.append("{:<20}".format(line))  # Align Arabic name
    bill_text.append("=" * 45)

    # Totals based on selected items
    bill_text.append("")
    bill_text.append(f"SubTotal:       AED {total_payment_amount:.2f}")
    bill_text.append(f"VAT (5%):       AED {vat:.2f}")
    bill_text.append("=" * 45)
    bill_text.append(f"Grand Total:    AED {total_payment_amount:.2f}")
    bill_text.append("=" * 45)

    # Payment details
    try:
        payment_instance = Payment.objects.get(id=payment)
        bill_text.append("Collection Details:")
        bill_text.append("")
        bill_text.append(f"Payment Method: {payment_instance.payment_method}")
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
        filename = f"invoice_{payment}.pdf"
        pdf_path, pdf_url = save_bill_as_pdf(formatted_bill_text, filename, logo_path)

    return formatted_bill_text, logo_path, pdf_url


def group_format_bill(orders, payment, total_payment_amount, vat, save_as_pdf=False):
    import textwrap
    from apps.order.models import Payment, OrderItems
    from django.utils.timezone import localtime

    bill_text = []

    # Header
    bill_text.append("=" * 45)
    bill_text.append("        TAX INVOICE        ")
    bill_text.append("=" * 45)
    bill_text.append("  Coffee Shop Co. L.L.C  ")
    bill_text.append("     Shop 1, Block A     ")
    bill_text.append("     Abraj Al Mamzar     ")
    bill_text.append("       Dubai, UAE        ")
    bill_text.append("Ct: 0547606099 / 0559803445")
    bill_text.append("TRN: 104340270800001")
    bill_text.append("=" * 45)
    bill_text.append("         Group Bill         ")
    bill_text.append("=" * 45)

    # Extract Order Details
    order_ids = [str(order.id) for order in orders]  # List of order IDs
    table_numbers = [
        str(order.table.table_number) if order.table else "N/A" for order in orders
    ]  # Table numbers
    total_pax = sum(order.number_of_pax or 0 for order in orders)  # Total pax
    earliest_check_in = min(
        order.created_at for order in orders
    )  # Earliest check-in time
    total_discount = sum(
        order.discount.value if order.discount else Decimal("0.00") for order in orders
    )  # Total discount

    # Invoice and Payment Details
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Invoice No: {payment}",
            f"Table: ({'-'.join(table_numbers)})",
        )
    )
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Order No: ({'-'.join(order_ids)})",
            f"No Of Pax: {total_pax}",
        )
    )
    bill_text.append(
        "{:<20} {:>20}".format(
            f"Bill Date: {localtime().strftime('%d-%m-%Y')}",
            f"Check Out: {localtime().strftime('%H:%M:%S')}",
        )
    )
    bill_text.append(f"Check In: {earliest_check_in.strftime('%H:%M:%S')}")

    bill_text.append("=" * 45)

    # Table Header
    bill_text.append(
        "{:<20} {:>6} {:>8} {:>10}".format("Item - UOM", "Qty", "Price", "Value")
    )
    bill_text.append("-" * 45)

    # Track unique items and their totals
    item_totals = {}

    for order in orders:
        order_items = OrderItems.objects.filter(order=order, remaining_quantity__gt=0)

        for item in order_items:
            product_name = item.product.name
            product_name_ar = item.product.name_ar
            quantity = item.quantity
            price = item.product.price
            total = quantity * price

            # Accumulate totals for the same items
            if product_name in item_totals:
                item_totals[product_name]["quantity"] += quantity
                item_totals[product_name]["total"] += total
            else:
                item_totals[product_name] = {
                    "quantity": quantity,
                    "price": price,
                    "total": total,
                }

    # Print all unique items
    for product_name, data in item_totals.items():
        wrapped_product_name = textwrap.wrap(product_name, width=20)
        wrapped_product_name_ar = textwrap.wrap(product_name_ar, width=20)

        # Print the first line of the product name with values
        bill_text.append(
            "{:<20} {:>6} {:<8.2f} {:<10.2f}".format(
                wrapped_product_name[0], data["quantity"], data["price"], data["total"]
            )
        )

        # Print additional lines for long names
        for line in wrapped_product_name[1:]:
            bill_text.append("{:<20}".format(line))
        # Print the Arabic product name below the English name
        for line in wrapped_product_name_ar:
            bill_text.append("{:<20}".format(line))  # Align Arabic name
    bill_text.append("=" * 45)

    # Totals
    bill_text.append("")
    bill_text.append(f"SubTotal:       AED {total_payment_amount:.2f}")
    bill_text.append(f"VAT (5%):       AED {vat:.2f}")

    bill_text.append(f"Discount:       AED -{total_discount:.2f}")

    bill_text.append("=" * 45)

    # Adjust the grand total after discount
    grand_total = total_payment_amount - total_discount
    bill_text.append(f"Grand Total:    AED {grand_total:.2f}")
    bill_text.append("=" * 45)

    # Payment Details
    try:
        payment_instance = Payment.objects.get(id=payment)
        bill_text.append("Collection Details:")
        bill_text.append("")
        bill_text.append(f"Payment Method: {payment_instance.payment_method}")
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
        filename = f"invoice_{payment}.pdf"
        pdf_path, pdf_url = save_bill_as_pdf(formatted_bill_text, filename, logo_path)

    return formatted_bill_text, logo_path, pdf_url


def save_bill_as_pdf(bill_text, filename, logo_path=None):
    """Save bill as a PDF file inside media/uploads/bills/ with Arabic support."""

    # Define the target directory inside the media folder
    bills_dir = os.path.join(settings.MEDIA_ROOT, "uploads", "bills")
    os.makedirs(bills_dir, exist_ok=True)  # Ensure directory exists

    # Generate the full PDF file path
    pdf_path = os.path.join(bills_dir, filename)

    # Delete existing PDF if exists
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
            print(f"Deleted existing bill: {pdf_path}")
        except Exception as e:
            print(f"Failed to delete existing bill: {e}")
            raise PermissionError(_("Unable to delete existing bill file."))

    # Create PDF using ReportLab
    c = canvas.Canvas(pdf_path, pagesize=letter)
    y_position = 750  # Start writing from the top

    # Load and register Arabic font
    arabic_font_path = os.path.join(
        settings.BASE_DIR, "fonts", "NotoSansArabic-VariableFont_wdth,wght.ttf"
    )
    pdfmetrics.registerFont(TTFont("ArabicFont", arabic_font_path))

    # Set font for Arabic support
    c.setFont("ArabicFont", 10)  # Use Arabic font instead of Helvetica

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

    # Write each line of the bill
    for line in bill_text.split("\n"):
        formatted_line = format_arabic_text(line)  # Apply Arabic text formatting
        c.drawString(50, y_position, formatted_line)
        y_position -= 15  # Adjust vertical spacing

        # If space runs out, start a new page
        if y_position < 50:
            c.showPage()
            c.setFont("ArabicFont", 10)  # Reset font on new page
            y_position = 750  # Reset the y position to the top of the new page

    c.save()
    print(f"Bill saved as PDF: {pdf_path}")

    # Generate public URL for the saved PDF
    pdf_relative_path = f"uploads/bills/{filename}"  # Relative path from MEDIA_URL
    pdf_url = urljoin(settings.MEDIA_URL, pdf_relative_path)

    return pdf_path, pdf_url  # Return both file path and public URL


def print_to_printer(printer_ip, bill_text, logo_path=None):
    try:
        printer = Network(printer_ip)

        # Print logo if provided
        if logo_path and os.path.exists(logo_path):
            logo = Image.open(logo_path).convert("L")  # Convert to grayscale
            logo = logo.resize(
                (256, int(logo.height * (256 / logo.width)))  # Reduce width to 256px
            )
            printer.set(align="center")  # Center alignment
            printer.image(logo)
            printer.text("\n")  # Add a newline after the logo

        # Print bill text
        printer.set(align="left")  # Reset alignment
        printer.text(bill_text + "\n")

        # Cut the paper
        printer.cut()
        printer.cashdraw(2)  # Open cash drawer

        print(f"Print job sent to printer at {printer_ip}")
    except Exception as e:
        print(f"Failed to print to {printer_ip}: {e}")


def generate_report(source):
    """
    Generate a detailed report based on business day or date.
    """
    from apps.order.models import Order, Payment, BusinessDay, OrderItems
    from apps.category.models import Category
    from decimal import Decimal

    if isinstance(source, BusinessDay):  # Z Report case
        orders = Order.objects.filter(
            business_day=source, is_deleted=False, is_paid=True
        )
        payments = Payment.objects.filter(business_day=source)
        business_day = source.start_time  # ✅ Correctly set datetime
    # else:  # X Report case (source is a date)
    #     business_day_obj = BusinessDay.objects.filter(
    #         start_time__date__lte=source,
    #         end_time__isnull=True,  # Only the currently open business day
    #     ).first()

    #     if business_day_obj:
    #         orders = Order.objects.filter(business_day=business_day_obj, is_deleted=False)
    #         payments = Payment.objects.filter(business_day=business_day_obj)
    #         business_day = business_day_obj.start_time  # ✅ Ensure it's a datetime
    #     else:
    #         orders = Order.objects.none()
    #         payments = Payment.objects.none()
    #         business_day = source  # ✅ Use source date as fallback

    # Totals
    total_sales = sum(order.final_total for order in orders)
    total_discounts = sum(order.discount.value for order in orders if order.discount)
    net_total = sum(order.grand_total for order in orders)

    # Collection Details
    cash_total = sum(payment.cash_amount for payment in payments)
    card_total = sum(payment.visa_amount for payment in payments)
    total_collection = sum(payment.amount for payment in payments)

    collection_details = {
        "cash_total": cash_total,
        "card_total": card_total,
        "total_collection": total_collection,
    }

    # Revenue Center Wise Collection (Cash & Card per Hall)
    halls_data = orders.values("hall").annotate(
        hall_sales=Sum("final_total"), guest_count=Sum("number_of_pax")
    )
    halls = [entry["hall"] for entry in halls_data]
    revenue_by_hall = {hall: {"cash": 0, "card": 0, "total": 0} for hall in halls}

    for payment in payments:
        for order in payment.orders.all():  # ManyToManyField
            hall_name = order.hall if order.hall else "Unknown"
            if payment.payment_method in ["cash", "multi"]:
                revenue_by_hall[hall_name]["cash"] += payment.cash_amount
            if payment.payment_method in ["card", "multi"]:
                revenue_by_hall[hall_name]["card"] += payment.visa_amount
            revenue_by_hall[hall_name]["total"] += payment.amount

    # Revenue Center Wise Sales
    sales_by_hall = {hall: 0 for hall in halls}
    for order in orders:
        sales_by_hall[order.hall] += order.final_total

    # Canceled Items Data
    canceled_items = {}

    for order in orders:
        for item in order.order_items.filter(cancelled_quantity__gt=0):
            product_name = item.product.name
            if product_name not in canceled_items:
                canceled_items[product_name] = {"quantity": 0, "total_loss": Decimal(0)}
            canceled_items[product_name]["quantity"] += item.cancelled_quantity
            canceled_items[product_name]["total_loss"] += (
                item.product.price * item.cancelled_quantity
            )

    # Shift Wise Guest Count & Sales
    shifts = ["morning", "evening"]
    shift_pax_details = {
        shift: {hall: {"guests": 0, "sales": 0} for hall in halls} for shift in shifts
    }

    for order in orders:
        shift_pax_details[order.shift][order.hall]["guests"] += order.number_of_pax
        shift_pax_details[order.shift][order.hall]["sales"] += order.final_total

    # Shift Wise Average Per Pax
    shift_avg_per_pax = {
        shift: {
            hall: {
                "guests": shift_pax_details[shift][hall]["guests"],
                "avg_per_guest": (
                    shift_pax_details[shift][hall]["sales"]
                    / shift_pax_details[shift][hall]["guests"]
                    if shift_pax_details[shift][hall]["guests"] > 0
                    else 0
                ),
            }
            for hall in halls
        }
        for shift in shifts
    }

    # Tax Details
    vat_collected = sum(order.vat for order in orders)

    # Sub Group Wise Sales
    sub_categories = Category.objects.filter(parent__isnull=False)  # Only subcategories
    sub_group_sales = {sub.name: 0 for sub in sub_categories}

    for order in orders:
        for item in order.order_items.all():
            for category in item.product.category.filter(
                parent__isnull=False
            ):  # Only subcategories
                sub_group_sales[category.name] += (
                    item.product.price * item.quantity
                ) / Decimal(
                    1.05
                )  # Price before VAT

    # Group Wise Sales
    categories = Category.objects.filter(parent__isnull=True)
    category_map = {
        sub.name: sub.parent.name for sub in sub_categories
    }  # Parent category mapping
    group_sales = {cat.name: 0 for cat in categories}

    for order in orders:
        for item in order.order_items.all():
            for category in item.product.category.all():
                parent_name = category_map.get(
                    category.name, category.name
                )  # Get parent or use itself
                group_sales[parent_name] += (
                    item.product.price * item.quantity
                ) / Decimal(1.05)

    # Discount Details
    discount_orders = [
        {
            "order_id": order.id,
            "discount_amount": order.discount.value,
            "final_total": order.final_total,
        }
        for order in orders
        if order.discount
    ]

    return {
        "business_day": business_day,
        "total_sales": total_sales,
        "total_discounts": total_discounts,
        "net_total": net_total,
        "cash_total": cash_total,
        "card_total": card_total,
        "total_collection": total_collection,
        "collection_details": collection_details,
        "revenue_by_hall": revenue_by_hall,
        "sales_by_hall": sales_by_hall,
        "shift_pax_details": shift_pax_details,
        "shift_avg_per_pax": shift_avg_per_pax,
        "vat_collected": vat_collected,
        "sub_group_sales": sub_group_sales,
        "group_sales": group_sales,
        "discount_orders": discount_orders,
        "canceled_items": canceled_items,
    }


def print_report(report_data, report_type):
    """
    Print the formatted Z or X report using a thermal printer, matching the PDF format.
    """

    try:
        from apps.printer.models import Printer

        # Get printer IP
        p = Printer.objects.filter(printer_type="cashier").first()
        printer_ip = p.ip_address
        printer = Network(printer_ip)

        # Helper Functions
        def print_centered(text, bold=True, size=2):
            printer.set(align="center", bold=bold, height=size, width=size)
            printer.text(text + "\n")

        def print_left_right(left_text, right_text, bold=False):
            printer.set(align="left", bold=bold, height=1, width=1)
            spacing = 32 - len(left_text) - len(str(right_text))
            printer.text(f"{left_text}{' ' * spacing}{right_text}\n")

        def print_line():
            printer.set(align="center", bold=False, height=1, width=1)
            printer.text("-" * 32 + "\n")

        # 1️ **Report Title & Date**
        print_centered("IBN EZZ COFFEE SHOP CO. L.L.C")
        print_centered(f"{report_type} REPORT")
        printer.set(align="center", bold=False, height=1, width=1)
        printer.text(f"DATE: {report_data['business_day']}\n")
        printer.text(f"PRINTED ON: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        print_line()

        # 2️ **Sales Summary**
        print_left_right("Total Sales:", f"{report_data['total_sales']:.2f}")
        print_left_right("Total Discounts:", f"{report_data['total_discounts']:.2f}")
        print_left_right("Net Total:", f"{report_data['net_total']:.2f}")
        print_line()

        # 3️ **Collection Details**
        print_centered("COLLECTION DETAILS", bold=True, size=1)
        print_left_right(
            "CASH:", f"{report_data['collection_details']['cash_total']:.2f}"
        )
        print_left_right(
            "CARD:", f"{report_data['collection_details']['card_total']:.2f}"
        )
        print_line()
        print_left_right(
            "TOTAL COLLECTION:",
            f"{report_data['collection_details']['total_collection']:.2f}",
            bold=True,
        )
        print_line()

        # 4️ **Tax Details**
        print_centered("TAX DETAILS", bold=True, size=1)
        print_left_right("VAT:", f"{report_data['vat_collected']:.2f}")
        print_line()

        # 5️ **Revenue Center Wise Collection**
        print_centered("REVENUE CENTER WISE COLLECTION", bold=True, size=1)
        for hall, revenue in report_data["revenue_by_hall"].items():
            print_centered(hall.upper(), bold=True, size=1)
            print_left_right("CASH:", f"{revenue['cash']:.2f}")
            print_left_right("CARD:", f"{revenue['card']:.2f}")
            print_left_right("TOTAL:", f"{revenue['total']:.2f}", bold=True)
            print_line()

        # 6️ **Shift Wise Hall Pax Details**
        print_centered("SHIFT WISE HALL PAX DETAILS", bold=True, size=1)
        printer.text(f"{'REVENUE CENTER':<15}{'GUESTS':>8}{'SALES':>10}\n")

        for shift, halls in report_data["shift_pax_details"].items():
            print_centered(shift.upper(), bold=True, size=1)
            for hall, details in halls.items():
                printer.text(
                    f"{hall.upper():<15}{details['guests']:>8}{details['sales']:>10.2f}\n"
                )

            printer.text(
                f"{'SHIFT TOTAL':<15}{sum(details['guests'] for details in halls.values()):>8}{sum(details['sales'] for details in halls.values()):>10.2f}\n"
            )
            print_line()

        # 7️ **Shift Wise Avg Per Pax**
        print_centered("SHIFT WISE AVG PER PAX", bold=True, size=1)
        printer.text(f"{'REVENUE CENTER':<15}{'GUESTS':>8}{'AVG/GUEST':>10}\n")

        for shift, halls in report_data["shift_avg_per_pax"].items():
            print_centered(shift.upper(), bold=True, size=1)
            for hall, details in halls.items():
                printer.text(
                    f"{hall.upper():<15}{details['guests']:>8}{details['avg_per_guest']:>10.2f}\n"
                )

            print_line()

        #  **Group-wise Sales**
        print_centered("GROUP-WISE SALES", bold=True, size=1)
        for category, sales in report_data["group_sales"].items():
            print_left_right(category.capitalize() + ":", f"{sales:.2f}")
        print_line()

        # 9️ **Sub Group-wise Sales**
        print_centered("SUB GROUP-WISE SALES", bold=True, size=1)
        for sub_category, sales in report_data["sub_group_sales"].items():
            print_left_right(sub_category.capitalize() + ":", f"{sales:.2f}")
        print_line()

        #  **Discounted Orders**
        print_centered("DISCOUNTED ORDERS", bold=True, size=1)
        if report_data["discount_orders"]:
            for discount in report_data["discount_orders"]:
                printer.text(
                    f"Order #{discount['order_id']} - Discount: {discount['discount_amount']:.2f}\n"
                )
        else:
            printer.text("NO DISCOUNTS APPLIED.\n")
        print_line()
        # Canceled Items
        print_centered("CANCELED ITEMS", bold=True, size=1)
        if report_data["canceled_items"]:
            for product, details in report_data["canceled_items"].items():
                print_left_right(
                    product, f"{details['quantity']} x {details['total_loss']:.2f}"
                )
        else:
            printer.text("NO CANCELED ITEMS\n")
        print_line()
        #  **End of Report**
        print_centered("END OF REPORT", bold=True, size=1)
        print_line()

        #  **Cut Paper**
        printer.cut()

        return True

    except Exception as e:
        return f"Printing failed: {str(e)}"


def save_report_as_pdf(report_data, report_type, date):
    """
    Generates a PDF report formatted for an 80mm thermal printer with dynamic page handling.
    """
    receipt_width = 220  # 80mm printer width
    pdf_height = 2000  # Increased height for long reports
    font_size = 10

    reports_dir = os.path.join(settings.MEDIA_ROOT, "uploads/reports")
    os.makedirs(reports_dir, exist_ok=True)

    pdf_filename = f"{report_type}_Report_{date}.pdf"
    pdf_path = os.path.join(reports_dir, pdf_filename)

    # Remove existing file
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    # Create PDF canvas
    c = canvas.Canvas(pdf_path, pagesize=(receipt_width, pdf_height))
    c.setFont("Courier-Bold", font_size)

    y = pdf_height - 20  # Initial Y position

    def check_page_break():
        """Creates a new page if y position is too low."""
        nonlocal y
        if y < 50:
            c.showPage()  # Create new page
            c.setFont("Courier-Bold", font_size)
            y = pdf_height - 20

    def draw_centered(text):
        """Draws centered text with page break handling."""
        nonlocal y  # Move this to the beginning
        check_page_break()
        c.drawCentredString(receipt_width / 2, y, text)
        y -= 15  # Now it correctly modifies y

    def draw_line():
        """Draws a horizontal line with page break handling."""
        nonlocal y
        check_page_break()
        c.line(10, y, receipt_width - 10, y)
        y -= 10

    # ✅ **Report Header**
    draw_centered("IBN EZZ COFFEE SHOP CO. L.L.C")
    draw_centered(f"{report_type} REPORT")
    draw_centered(f"DATE: {report_data['business_day']}")
    draw_centered(f"PRINTED ON: {datetime.now().strftime('%H:%M:%S')}")
    draw_line()

    # ✅ **Sales Summary**
    c.drawString(10, y, f"Total Sales: {report_data['total_sales']:.2f}")
    y -= 15
    c.drawString(10, y, f"Total Discounts: {report_data['total_discounts']:.2f}")
    y -= 15
    c.drawString(10, y, f"Net Total: {report_data['net_total']:.2f}")
    y -= 20
    draw_line()

    # ✅ **Collection Details**
    draw_centered("COLLECTION DETAILS")
    collection = report_data["collection_details"]

    c.drawString(10, y, "CARD:")
    c.drawRightString(receipt_width - 10, y, f"{collection['card_total']:.2f}")
    y -= 15

    c.drawString(10, y, "CASH:")
    c.drawRightString(receipt_width - 10, y, f"{collection['cash_total']:.2f}")
    y -= 15

    draw_line()

    c.drawString(10, y, "TOTAL COLLECTION:")
    c.drawRightString(receipt_width - 10, y, f"{collection['total_collection']:.2f}")
    y -= 20
    draw_line()

    # ✅ **Tax Details**
    draw_centered("TAX DETAILS")
    c.drawString(10, y, f"VAT: {report_data['vat_collected']:.2f}")
    y -= 15
    draw_line()

    # ✅ **Revenue Center Wise Collection**
    draw_centered("REVENUE CENTER WISE COLLECTION")
    for hall, revenue in report_data["revenue_by_hall"].items():
        check_page_break()
        c.drawString(10, y, hall.upper())
        y -= 15
        c.drawString(20, y, f"CASH: {revenue['cash']:.2f}")
        y -= 15
        c.drawString(20, y, f"CARD: {revenue['card']:.2f}")
        y -= 15
        c.drawString(20, y, f"TOTAL: {revenue['total']:.2f}")
        y -= 20
        draw_line()

    # ✅ **Shift Wise Hall Pax Details**
    draw_centered("SHIFT WISE HALL PAX DETAILS")
    c.drawString(10, y, f"{'REVENUE CENTER':<15}{'GUESTS':>8}{'SALES':>10}")
    y -= 15

    for shift, halls in report_data["shift_pax_details"].items():
        check_page_break()
        c.drawString(10, y, shift.upper())
        y -= 15
        for hall, details in halls.items():
            c.drawString(
                10,
                y,
                f"{hall.upper():<15}{details['guests']:>8}{details['sales']:>10.2f}",
            )
            y -= 15
        draw_line()

    # ✅ **Shift Wise Avg Per Pax**
    draw_centered("SHIFT WISE AVG PER PAX")
    c.drawString(10, y, f"{'REVENUE CENTER':<15}{'GUESTS':>8}{'AVG/GUEST':>10}")
    y -= 15

    for shift, halls in report_data["shift_avg_per_pax"].items():
        check_page_break()
        c.drawString(10, y, shift.upper())
        y -= 15
        for hall, details in halls.items():
            c.drawString(
                10,
                y,
                f"{hall.upper():<15}{details['guests']:>8}{details['avg_per_guest']:>10.2f}",
            )
            y -= 15
        draw_line()

    # ✅ **Group-wise Sales**
    draw_centered("GROUP-WISE SALES")
    for category, sales in report_data["group_sales"].items():
        check_page_break()
        c.drawString(10, y, f"{category.capitalize()}: {sales:.2f}")
        y -= 15
    draw_line()

    # ✅ **Sub Group-wise Sales**
    draw_centered("SUB GROUP-WISE SALES")
    for sub_category, sales in report_data["sub_group_sales"].items():
        check_page_break()
        c.drawString(10, y, f"{sub_category.capitalize()}: {sales:.2f}")
        y -= 15
    draw_line()

    # ✅ **Discounted Orders**
    draw_centered("DISCOUNTED ORDERS")
    if report_data["discount_orders"]:
        for discount in report_data["discount_orders"]:
            check_page_break()
            c.drawString(
                10,
                y,
                f"Order #{discount['order_id']} - Discount: {discount['discount_amount']:.2f}",
            )
            y -= 15
    else:
        c.drawString(10, y, "NO DISCOUNTS APPLIED.")
        y -= 15
    draw_line()
    # Canceled Items
    draw_centered("CANCELED ITEMS")
    if report_data["canceled_items"]:
        for product, details in report_data["canceled_items"].items():
            check_page_break()
            c.drawString(
                10, y, f"{product}: {details['quantity']} x {details['total_loss']:.2f}"
            )
            y -= 15
    else:
        c.drawString(10, y, "NO CANCELED ITEMS")
        y -= 15
    draw_line()
    # ✅ **End of Report**
    draw_centered("END OF REPORT")
    draw_line()

    # ✅ **Save and Return PDF URL**
    c.save()
    pdf_url = f"{settings.MEDIA_URL}uploads/reports/{pdf_filename}"

    return pdf_url


def generate_sales_report(source):
    """
    Generates a sales report for a given business day or a specific date.

    :param source: BusinessDay instance or a specific date (for X Report).
    :return: Dictionary containing sales report data.
    """
    from apps.order.models import Payment, BusinessDay

    # Determine whether we're generating for a closed BusinessDay (Z Report) or an ongoing date (X Report)
    if isinstance(source, BusinessDay):
        payments = Payment.objects.filter(business_day=source)
        business_day_date = source.start_time.date()
    else:
        payments = Payment.objects.filter(created_at__date=source)
        business_day_date = source  # Just a date

    if not payments.exists():
        return {"detail": _("No transactions for this business day")}

    # Data aggregation
    report_data = defaultdict(list)
    total_amount = Decimal("0.00")

    for payment in payments:
        for order in payment.orders.all():
            report_data[order.hall].append(
                {
                    "bill_no": payment.id,
                    "payment_type": payment.payment_method.upper(),
                    "time": payment.created_at.strftime("%I:%M %p"),
                    "total": payment.amount,
                }
            )
        total_amount += payment.amount  # Summing up total sales amount

    # Collection breakdown
    collection_details = {
        "cash_total": sum(payment.cash_amount for payment in payments),
        "card_total": sum(payment.visa_amount for payment in payments),
        "total_collection": sum(payment.amount for payment in payments),
    }

    return {
        "business_day": business_day_date.strftime("%d-%m-%Y"),
        "printed_at": now().strftime("%d-%m-%Y %I:%M %p"),
        "revenue_centers": dict(report_data),
        "total_bills": payments.count(),
        "total_amount": total_amount,
        "collection_details": collection_details,
    }


def print_sales_report(sales_report):
    """
    Prints the sales report using the Rocket 300 thermal printer.
    The report is formatted for 80mm paper width.
    """
    from apps.printer.models import Printer

    try:
        # Get cashier printer details
        p = Printer.objects.filter(printer_type="cashier").first()
        if not p:
            raise ValueError("No cashier printer found.")

        printer_ip = p.ip_address
        printer = Network(printer_ip)

        # 🏷️ Print header
        printer.set(align="center", bold=True, width=2, height=2)
        printer.text("IBN EZZ COFFEE SHOP\n")
        printer.set(align="center", bold=True, width=1, height=1)
        printer.text("Bill No Wise Sales Report\n")
        printer.text(f"For: {sales_report['business_day']}\n")
        printer.text(f"Printed on: {sales_report['printed_at']}\n")
        printer.text("-" * 32 + "\n")

        # 🏷️ Print revenue centers & transactions
        for center, transactions in sales_report["revenue_centers"].items():
            total_per_center = 0
            bill_count = len(transactions)  # Count of bills

            printer.set(align="left", bold=True)
            printer.text(f"Revenue Center: {center}\n")
            printer.text("-" * 32 + "\n")

            # 📌 Print Table Header (Aligned)
            printer.set(align="left", bold=True)
            printer.text(f"{'BillNo':<6} {'P.Type':<7} {'Time':<8} {'Total':>7}\n")
            printer.text("-" * 32 + "\n")

            # 📌 Print Transactions
            for txn in transactions:
                bill_no = f"{txn['bill_no']:<6}"  # Left align (6 chars)
                p_type = f"{txn['payment_type']:<7}"  # Left align (7 chars)
                time = f"{txn['time']:<8}"  # Left align (8 chars)
                total = (
                    f"{txn['total']:>7.2f}"  # Right align (7 chars, 2 decimal places)
                )

                printer.text(f"{bill_no}{p_type}{time}{total}\n")
                total_per_center += txn["total"]

            # 📌 Print Totals per Revenue Center
            printer.text("-" * 32 + "\n")
            printer.set(align="left", bold=True)
            printer.text(
                f"Total Bills: {bill_count:<5}  Total: {total_per_center:.2f}\n\n"
            )

        # 🏷️ Final Summary Separator
        printer.text("-" * 32 + "\n")

        # 📌 Print Overall Totals
        printer.set(align="left", bold=True)
        printer.text(f"Total Bills: {sales_report['total_bills']}\n")
        printer.text(f"Total Amount: {sales_report['total_amount']:.2f}\n\n")

        # 🏷️ Collection Details
        printer.text("Collection Details\n")
        printer.text(
            f"CASH  : {sales_report['collection_details']['cash_total']:.2f}\n"
        )
        printer.text(
            f"CARD  : {sales_report['collection_details']['card_total']:.2f}\n"
        )
        printer.text(
            f"Total : {sales_report['collection_details']['total_collection']:.2f}\n"
        )

        # 🏷️ Cut and Finish
        printer.text("\n\n")
        printer.cut()
        printer.close()

    except Exception as e:
        print(f"Error printing report: {e}")
        return f"Printing failed: {e}"


def save_sales_report_as_pdf(sales_report, file_path):
    """
    Saves the sales report as a PDF, formatted for an 80mm thermal printer.
    """
    c = canvas.Canvas(
        file_path, pagesize=(226, 1000)
    )  # Increased height for longer reports
    y_position = 980  # Start from top

    # Header
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(113, y_position, "IBN EZZ COFFEE SHOP CO. L.L.C")
    y_position -= 15
    c.setFont("Helvetica", 9)
    c.drawCentredString(113, y_position, "Bill No Wise Sales Report")
    y_position -= 12
    c.drawCentredString(113, y_position, f"For: {sales_report['business_day']}")
    y_position -= 12
    c.drawCentredString(113, y_position, f"Printed on: {sales_report['printed_at']}")
    y_position -= 20

    # Revenue Centers
    for center, transactions in sales_report["revenue_centers"].items():
        total_per_center = 0  # To calculate sum per center
        bill_count = len(transactions)  # Get count of bills for the center

        c.setFont("Helvetica-Bold", 9)
        y_position -= 12
        c.drawString(5, y_position, f"Revenue Center: {center}")
        y_position -= 12

        # Table Header (Fixed positions)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(5, y_position, "BillNo")  # Column 1
        c.drawString(50, y_position, "P.Type")  # Column 2
        c.drawString(100, y_position, "Time")  # Column 3
        c.drawString(160, y_position, "Total")  # Column 4
        y_position -= 10
        c.line(5, y_position, 221, y_position)  # Draw a separator line
        y_position -= 12

        # Transactions
        for txn in transactions:
            bill_no = str(txn["bill_no"])
            p_type = txn["payment_type"]
            time = txn["time"]
            total = f"{txn['total']:.2f}"

            # Draw each value in its correct column
            c.drawString(5, y_position, bill_no)  # Column 1
            c.drawString(50, y_position, p_type)  # Column 2
            c.drawString(100, y_position, time)  # Column 3
            c.drawString(160, y_position, total)  # Column 4
            y_position -= 12
            total_per_center += txn["total"]

        # Separator Line
        c.line(5, y_position, 221, y_position)
        y_position -= 12

        # Show Bill Count and Total for Revenue Center
        c.setFont("Helvetica-Bold", 9)
        c.drawString(5, y_position, f"Total Bills: {bill_count}")  # Show bill count
        c.drawString(
            120, y_position, f"Total: {total_per_center:.2f}"
        )  # Show total amount
        y_position -= 20  # Extra spacing after each center

    # Final Summary Separator
    c.line(5, y_position, 221, y_position)
    y_position -= 12

    # Total Summary
    c.setFont("Helvetica-Bold", 9)
    c.drawString(5, y_position, f"Total Bills: {sales_report['total_bills']}")
    y_position -= 12
    c.drawString(5, y_position, f"Total Amount: {sales_report['total_amount']:.2f}")
    y_position -= 20

    # Collection Details
    c.setFont("Helvetica-Bold", 9)
    c.drawString(5, y_position, "Collection Details")
    y_position -= 12
    c.setFont("Helvetica", 8)
    c.drawString(
        5, y_position, f"CASH  : {sales_report['collection_details']['cash_total']:.2f}"
    )
    y_position -= 10
    c.drawString(
        5, y_position, f"CARD  : {sales_report['collection_details']['card_total']:.2f}"
    )
    y_position -= 10
    c.drawString(
        5,
        y_position,
        f"Total : {sales_report['collection_details']['total_collection']:.2f}",
    )
    y_position -= 20

    c.save()
    return file_path


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
