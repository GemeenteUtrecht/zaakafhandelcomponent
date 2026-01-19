import factory


class KillableTaskFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"task-{n}")

    class Meta:
        model = "camunda.KillableTask"
