import factory
from faker import Faker

from ..models import LandingPageConfiguration, LandingPageLink, LandingPageSection

fake = Faker()


class LandingPageConfigurationFactory(factory.django.DjangoModelFactory):
    title = factory.LazyAttribute(lambda x: fake.sentence())
    image = factory.django.ImageField(filename="example.jpg")

    class Meta:
        model = LandingPageConfiguration


class LandingPageSectionFactory(factory.django.DjangoModelFactory):
    name = factory.LazyAttribute(lambda x: fake.word())
    icon = factory.LazyAttribute(lambda x: fake.word())
    landing_page_configuration = factory.SubFactory(LandingPageConfigurationFactory)

    class Meta:
        model = LandingPageSection
        django_get_or_create = ("landing_page_configuration",)


class LandingPageLinkFactory(factory.django.DjangoModelFactory):
    label = factory.LazyAttribute(lambda x: fake.word())
    href = factory.LazyAttribute(lambda x: fake.url())

    class Meta:
        model = LandingPageLink

    class Params:
        with_icon = factory.Trait(icon=factory.LazyAttribute(lambda x: fake.word()))
        with_configuration = factory.Trait(
            landing_page_configuration=factory.SubFactory(
                LandingPageConfigurationFactory
            )
        )
        with_section = factory.Trait(
            landing_page_section=factory.SubFactory(LandingPageSectionFactory)
        )
