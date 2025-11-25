from django.conf import settings
from rest_framework import serializers
from services.models import Months, Months_calculation, Month_indicators, CustomUser


class MonthsListSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Months
        fields = [
            "month_id",
            "month_name",
            "main_value",
            "image_url",
        ]

    def get_image_url(self, obj):
        bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "apple-media")
        base = getattr(settings, "AWS_S3_ENDPOINT_URL", "http://localhost:9000").rstrip("/")
        image_key = obj.month_image or "placeholder.png"
        return f"{base}/{bucket}/{image_key}"


class MonthsCreateUpdateSerializer(serializers.ModelSerializer):
    month_id = serializers.IntegerField(read_only=True)
    class Meta:
        model = Months
        # month_image не изменяется здесь
        fields = [
            "month_id",
            "month_name",
            "description",
            "main_value",
            "status",
            "base_yield",
            "ideal_temp",
            "ideal_precip",
            "temperature",
            "precipitation",
        ]


class MonthIndicatorsSerializer(serializers.ModelSerializer):
    service = MonthsListSerializer(read_only=True)

    class Meta:
        model = Month_indicators
        fields = [
            "service",
            "sum_precipitation",
            "avg_temp",
            "comment",
        ]


class MonthsCalculationListSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    moderator_email = serializers.EmailField(source="moderator.email", read_only=True)

    class Meta:
        model = Months_calculation
        fields = [
            "id",
            "status",
            "created_at",
            "submitted_at",
            "finished_at",
            "created_by_email",
            "moderator_email",
            "location",
            "person",
            "result_value",
        ]


class MonthsCalculationDetailSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = Months_calculation
        fields = [
            "id",
            "status",
            "created_at",
            "submitted_at",
            "finished_at",
            "location",
            "person",
            "result_value",
            "items",
        ]

    def get_items(self, obj):
        qs = Month_indicators.objects.select_related("service").filter(order=obj)
        return MonthIndicatorsSerializer(qs, many=True).data


class MonthsCalculationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Months_calculation
        fields = [
            "location",
            "person",
        ]


class MonthsCartSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(allow_null=True)
    items_count = serializers.IntegerField()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class MeSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
class UserSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(default=False, required=False)
    is_superuser = serializers.BooleanField(default=False, required=False)

    class Meta:
        model = CustomUser
        fields = ["email", "password", "is_staff", "is_superuser"]
        extra_kwargs = {"password": {"write_only": True}}



