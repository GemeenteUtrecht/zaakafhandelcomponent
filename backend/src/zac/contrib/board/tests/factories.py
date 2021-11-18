from django.utils.text import slugify

import factory
import factory.fuzzy

from ..constants import BoardObjectTypes


class BoardFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: factory.Faker("word").generate() + f"-{n}")
    slug = factory.LazyAttribute(lambda a: slugify(a.name))

    class Meta:
        model = "board.Board"


class BoardColumnFactory(factory.django.DjangoModelFactory):
    board = factory.SubFactory(BoardFactory)
    name = factory.Sequence(lambda n: factory.Faker("word").generate() + f"-{n}")
    slug = factory.LazyAttribute(lambda a: slugify(a.name))
    order = factory.Sequence(lambda n: n)

    class Meta:
        model = "board.BoardColumn"


class BoardItemFactory(factory.django.DjangoModelFactory):
    column = factory.SubFactory(BoardColumnFactory)
    object_type = BoardObjectTypes.zaak
    object = factory.Faker("url")

    class Meta:
        model = "board.BoardItem"
