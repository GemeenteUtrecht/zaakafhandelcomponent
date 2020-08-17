import factory


class ActivityFactory(factory.django.DjangoModelFactory):
    zaak = factory.Faker("url")
    name = factory.Faker("bs")

    class Meta:
        model = "activities.Activity"


class EventFactory(factory.django.DjangoModelFactory):
    activity = factory.SubFactory(ActivityFactory)
    notes = factory.Faker("bs")

    class Meta:
        model = "activities.Event"
