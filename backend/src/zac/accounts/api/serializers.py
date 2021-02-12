from datetime import date

from rest_framework import serializers

from ..constants import AccessRequestResult
from ..models import AccessRequest, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "is_staff",
            "email",
        )


class CatalogusURLSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=1000, required=True)


class ZaakAccessSerializer(serializers.ModelSerializer):
    requester = serializers.SlugRelatedField(
        slug_field="username", queryset=User.objects.all()
    )
    handler = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = AccessRequest
        fields = (
            "requester",
            "handler",
            "zaak",
            "comment",
            "result",
            "start_date",
            "end_date",
        )
        extra_kwargs = {"result": {"read_only": True}}

    def validate(self, data):
        valid_data = super().validate(data)

        # todo validation - existing zaak access

        return valid_data

    def create(self, validated_data):
        request = self.context["request"]
        start_date = date.today()

        validated_data.update(
            {
                "handler": request.user,
                "result": AccessRequestResult.approve,
                "start_date": start_date,
            }
        )
        # todo close other pending access requests

        return super().create(validated_data)
