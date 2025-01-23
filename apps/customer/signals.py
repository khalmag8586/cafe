from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.cart.models import Cart,Wishlist
from apps.customer.models import Customer


@receiver(post_save, sender=Customer)
def create_cart_for_new_customer(sender, instance, created, **kwargs):
    if created:
        Cart.objects.create(customer=instance)
        Wishlist.objects.create(customer=instance)
