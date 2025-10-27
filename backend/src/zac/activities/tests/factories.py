import factory
from faker import Faker

from ..constants import ActivityStatuses

fake = Faker()


class ActivityFactory(factory.django.DjangoModelFactory):
    zaak = factory.LazyAttribute(lambda x: fake.url())
    name = factory.LazyAttribute(lambda x: fake.bs())
    status = ActivityStatuses.on_going

    class Meta:
        model = "activities.Activity"
        # To avoid database integrity errors because of unique constraint on model
        django_get_or_create = (
            "zaak",
            "name",
        )


class EventFactory(factory.django.DjangoModelFactory):
    activity = factory.SubFactory(ActivityFactory)
    notes = factory.LazyAttribute(lambda x: fake.bs())

    class Meta:
        model = "activities.Event"
