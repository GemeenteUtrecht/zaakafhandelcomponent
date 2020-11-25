import factory


class OrganisatieOnderdeelFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("bs")
    slug = factory.Sequence(lambda n: f"oo-{n}")

    class Meta:
        model = "organisatieonderdelen.OrganisatieOnderdeel"
