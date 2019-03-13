import factory
import factory.fuzzy

from ..constants import APITypes


class ServiceFactory(factory.django.DjangoModelFactory):
    label = factory.Faker('bs')
    api_type = factory.fuzzy.FuzzyChoice(APITypes.values)
    api_root = factory.Faker('url')

    class Meta:
        model = 'config.Service'
