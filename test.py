# import io
# from PIL import Image, ImageDraw, ImageFont
# from arabic_reshaper import arabic_reshaper
# from bidi.algorithm import get_display

# def format_arabic_text(text):
#     """Reshape and reorder Arabic text for proper rendering."""
#     reshaped_text = arabic_reshaper.reshape(text)
#     bidi_text = get_display(reshaped_text)
#     return bidi_text
# def arabic_text_to_image(text, font_path, font_size=18, output_filename="output.png"):
#     """Convert Arabic text to an image and display it for testing"""

#     # Load the Arabic font
#     font = ImageFont.truetype(font_path, font_size)
#     # Measure text size and position
#     dummy_img = Image.new("RGB", (1000, 500), "white")  # Large temporary image
#     dummy_draw = ImageDraw.Draw(dummy_img)
#     text_bbox = dummy_draw.textbbox((0, 0), text, font=font)
#     # Extract text dimensions
#     text_width = text_bbox[2] - text_bbox[0]
#     text_height = text_bbox[3] - text_bbox[1]
#     text_offset_y = text_bbox[1]  # Top offset to adjust spacing
#     # Measure text size for dynamic image width & height
#     # Create an optimized image
#     img_width = max(536, text_width + 20)  # Ensure enough width
#     img_height = text_height + 10  # Reduce unnecessary space

#     # Create a white image
#     img = Image.new("RGB", (img_width, img_height), "white")
#     draw = ImageDraw.Draw(img)

#     # Draw the text
#     draw.text((10, -text_offset_y + 5), text, font=font, fill="black")  # Adjust text positioning

#     # ✅ Save the image for testing
#     img.save(output_filename)
#     print(f"✅ Image saved as {output_filename}")

#     # ✅ Show the image for visual confirmation
#     img.show()

#     return output_filename

# # 🔹 Test the function
# if __name__ == "__main__":
#     test_text = "زجاجة مياه صغيرة"
#     font_path = r"C:\gigs\CAFE\cafe\fonts\Amiri-Regular.ttf"  # Update with your actual path
#     arabic_text_to_image(format_arabic_text(test_text), font_path)

# import usb.core
# import usb.util

# devices = usb.core.find(find_all=True)
# for device in devices:
#     print(f"Vendor ID: {hex(device.idVendor)}, Product ID: {hex(device.idProduct)}")

from escpos.printer import Usb

p = Usb(0x1504, 0x1f)  # Replace with your actual Vendor ID and Product ID
p.text("Hello, World!\n")
p.cut()