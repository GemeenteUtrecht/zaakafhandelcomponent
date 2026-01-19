from operator import attrgetter
from typing import Any, Iterable, List


def sort(iterable: Iterable, attributes: List[str]) -> List[Any]:
    """
    Sort an iterable based on attributes of each item.

    Example usage::

        >>> sort(some_list, attributes=["start", "-end"])
    """
    items = iterable

    for attribute in attributes[::-1]:
        reverse = attribute.startswith("-")
        attribute = attribute if not reverse else attribute[1:]
        items = sorted(items, key=attrgetter(attribute), reverse=reverse)

    return items
