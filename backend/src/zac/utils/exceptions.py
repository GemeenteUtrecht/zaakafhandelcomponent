from django.forms.utils import ErrorList


def get_error_list(errors):
    """
    Given a DRF Serializer.errors, return a Django ErrorList
    """
    return ErrorList(
        [
            f"{key}: {value}"
            for key, value_list in errors.items()
            for value in value_list
        ]
    )
