import factory


class ChecklistTypeFactory(factory.django.DjangoModelFactory):
    zaaktype_identificatie = factory.Faker("bs")
    zaaktype_catalogus = factory.Faker("url")

    class Meta:
        model = "checklists.ChecklistType"


class ChecklistQuestionFactory(factory.django.DjangoModelFactory):
    checklisttype = factory.SubFactory(ChecklistTypeFactory)
    order = factory.Faker("pyint", min_value=0)

    class Meta:
        model = "checklists.ChecklistQuestion"
        django_get_or_create = ("order", "checklisttype")


class QuestionChoiceFactory(factory.django.DjangoModelFactory):
    question = factory.Faker(ChecklistQuestionFactory)

    class Meta:
        model = "checklists.QuestionChoice"


class ChecklistFactory(factory.django.DjangoModelFactory):
    zaak = factory.Faker("url")
    checklisttype = factory.SubFactory(ChecklistTypeFactory)

    class Meta:
        model = "checklists.Checklist"


class ChecklistAnswerFactory(factory.django.DjangoModelFactory):
    checklist = factory.SubFactory(ChecklistFactory)

    class Meta:
        model = "checklists.ChecklistAnswer"
