import factory


class ChecklistTypeFactory(factory.django.DjangoModelFactory):
    zaaktype = factory.Faker("url")
    zaaktype_omschrijving = factory.Faker("bs")
    zaaktype_catalogus = factory.Faker("url")

    class Meta:
        model = "checklists.ChecklistType"


class ChecklistQuestionFactory(factory.django.DjangoModelFactory):
    checklist_type = factory.SubFactory(ChecklistTypeFactory)
    order = factory.Faker("int")

    class Meta:
        model = "checklists.ChecklistQuestion"
        django_get_or_create = ("order", "checklist_type")


class QuestionChoiceFactory(factory.django.DjangoModelFactory):
    question = factory.Faker(ChecklistQuestionFactory)

    class Meta:
        model = "checklists.QuestionChoice"


class ChecklistFactory(factory.django.DjangoModelFactory):
    zaak = factory.Faker("url")
    checklist_type = factory.SubFactory(ChecklistTypeFactory)

    class Meta:
        model = "checklists.Checklist"


class ChecklistAnswerFactory(factory.django.DjangoModelFactory):
    checklist = factory.SubFactory(ChecklistFactory)

    class Meta:
        model = "checklists.ChecklistAnswer"
