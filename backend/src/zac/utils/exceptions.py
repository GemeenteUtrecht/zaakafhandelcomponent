from django.forms.utils import ErrorList


def get_error_list(errors):
    """
    Given a DRF Serializer.errors, return a Django ErrorList
    """
    error_list = []
    for key, value_list in errors.items():
        for value in value_list:
            error_list.append(f"{key}: {value}")
    return ErrorList(error_list)
