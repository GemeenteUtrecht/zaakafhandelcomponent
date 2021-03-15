from rest_framework import serializers

from zac.accounts.models import User


class UserValidator:
    def __call__(self, username):
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            msg = "A user with username %s does not exist."
            raise serializers.ValidationError(msg)
