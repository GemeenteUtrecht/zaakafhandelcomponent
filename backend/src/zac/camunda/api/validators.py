from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from zac.accounts.models import User


class UserValidator:
    message = _("A user with `username` {username} does not exist.")

    def __call__(self, username):
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError(self.message.format(username=username))


class GroupValidator:
    message = _("A group with `name` {name} does not exist.")

    def __call__(self, name):
        try:
            Group.objects.get(name=name)
        except Group.DoesNotExist:
            raise serializers.ValidationError(self.message.format(name=name))


class OrValidator:
    def __init__(self, *validators):
        self.validators = validators

    def __call__(self, value):
        errors = []
        for validator in self.validators:
            try:
                validator(value)
            except serializers.ValidationError as err:
                errors.append(err.detail[0])
        if len(errors) == len(self.validators):
            raise serializers.ValidationError(" ".join(errors))
