import factory

from ..models import LandingPageConfiguration, LandingPageSection, LandingPageLink


class LandingPageConfigurationFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("sentence")
    image = factory.django.ImageField(filename="example.jpg")

    class Meta:
        model = LandingPageConfiguration


class LandingPageSectionFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("word")
    icon = factory.Faker("word")
    landing_page_configuration = factory.SubFactory(LandingPageConfigurationFactory)

    class Meta:
        model = LandingPageSection
        django_get_or_create = ('landing_page_configuration',)


class LandingPageLinkFactory(factory.django.DjangoModelFactory):
    label = factory.Faker("word")
    href = factory.Faker("url")

    class Meta:
        model = LandingPageLink

    class Params:
        with_icon = factory.Trait(
            icon=factory.Faker("word")
        )
        with_configuration = factory.Trait(
            landing_page_configuration=factory.SubFactory(LandingPageConfigurationFactory)
        )
        with_section = factory.Trait(
            landing_page_section=factory.SubFactory(LandingPageSectionFactory)
        )
