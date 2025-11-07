import factory
from faker import Faker

fake = Faker()


class OrganisatieOnderdeelFactory(factory.django.DjangoModelFactory):
    name = factory.LazyAttribute(lambda x: fake.bs())
    slug = factory.Sequence(lambda n: f"oo-{n}")

    class Meta:
        model = "organisatieonderdelen.OrganisatieOnderdeel"
