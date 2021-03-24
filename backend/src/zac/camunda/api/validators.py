from django.utils.translation import gettext_lazy as _

from rest_framework import serializers, validators

from zac.accounts.models import User


class UserValidator:
    message = _("A user with username {username} does not exist.")

    def __call__(self, username):
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError(self.message.format(username=username))
