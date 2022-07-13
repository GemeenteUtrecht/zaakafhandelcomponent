import factory
import factory.fuzzy
from zgw_consumers.api_models.constants import RolTypes


class CamundaStartProcessFactory(factory.django.DjangoModelFactory):
    zaaktype_identificatie = factory.Faker("bs")
    zaaktype_catalogus = factory.Faker("url")
    process_definition_key = factory.Faker("bs")

    class Meta:
        model = "start_process.CamundaStartProcess"


class ProcessEigenschapFactory(factory.django.DjangoModelFactory):
    camunda_start_process = factory.SubFactory(CamundaStartProcessFactory)
    eigenschapnaam = factory.Faker("bs")
    label = factory.Faker("bs")

    class Meta:
        model = "start_process.ProcessEigenschap"
        django_get_or_create = ("eigenschapnaam", "camunda_start_process")


class ProcessEigenschapChoiceFactory(factory.django.DjangoModelFactory):
    process_eigenschap = factory.Faker(ProcessEigenschapFactory)
    label = factory.Faker("bs")
    value = factory.Faker("bs")

    class Meta:
        model = "start_process.ProcessEigenschapChoice"


class ProcessInformatieObjectFactory(factory.django.DjangoModelFactory):
    camunda_start_process = factory.SubFactory(CamundaStartProcessFactory)
    informatieobjecttype_omschrijving = factory.Faker(ProcessEigenschapFactory)
    label = factory.Faker("bs")
    allow_multiple = factory.Faker("boolean")

    class Meta:
        model = "start_process.ProcessInformatieObject"
        django_get_or_create = (
            "informatieobjecttype_omschrijving",
            "camunda_start_process",
        )


class ProcessRolFactory(factory.django.DjangoModelFactory):
    camunda_start_process = factory.SubFactory(CamundaStartProcessFactory)
    roltype_omschrijving = factory.Faker("bs")
    betrokkene_type = factory.fuzzy.FuzzyChoice(RolTypes.labels.keys())
    label = factory.Faker("bs")

    class Meta:
        model = "start_process.ProcessRol"
        django_get_or_create = (
            "roltype_omschrijving",
            "camunda_start_process",
        )
