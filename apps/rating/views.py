from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.db import IntegrityError

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.rating.models import Rating
from apps.rating.serializers import RatingSerializer, RatingDialogSerializer

from cafe.pagination import StandardResultsSetPagination
from cafe.custom_permissions import OnlyCustomer, CustomerPermission


class RatingCreateView(generics.CreateAPIView):
    serializer_class = RatingSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]

    def perform_create(self, serializer):
        customer = self.request.user.customer
        serializer.save(created_by=customer)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
            created_object_id = serializer.instance.id

            return Response(
                {
                    "detail": _("Rating created successfully"),
                    "rating_id": created_object_id,
                },
                status=status.HTTP_201_CREATED,
            )
        except IntegrityError:
            # Find the existing rating
            customer = request.user.customer
            product = serializer.validated_data["product"]
            existing_rating = Rating.objects.get(created_by=customer, product=product)

            return Response(
                {
                    "detail": _("This product has already been rated by you."),
                    "status": "551",
                    "rating_id": existing_rating.id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class RatingListView(generics.ListAPIView):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]


class RatingRetrieveView(generics.RetrieveAPIView):
    serializer_class = RatingSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]
    lookup_field = "id"

    def get_object(self):
        rating_id = self.request.query_params.get("rating_id")
        rating = get_object_or_404(Rating, id=rating_id)
        return rating


class RatingUpdateView(generics.UpdateAPIView):
    serializer_class = RatingSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [OnlyCustomer]
    lookup_field = "id"

    def get_object(self):
        rating_id = self.request.query_params.get("rating_id")
        rating = get_object_or_404(Rating, id=rating_id)
        return rating

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user.customer)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {"detail": _("Rating Updated successfully")}, status=status.HTTP_200_OK
        )


class RatingDeleteView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def delete(self, request, *args, **kwargs):
        rating_ids = request.data.get("rating_id", [])
        for rating_id in rating_ids:
            instance = get_object_or_404(Rating, id=rating_id)
            instance.delete()
        return Response({"detail": _("Rating deleted successfully")})


class RatingDialogView(generics.ListAPIView):
    serializer_class = RatingDialogSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]
    queryset = Rating.objects.all()
