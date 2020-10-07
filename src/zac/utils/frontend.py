from typing import Dict

from django import forms


def get_form_data(form: forms.Form) -> Dict[str, Dict]:
    """
    Serialize the form data and errors for the frontend.
    """
    errors = (
        {
            field: [{"msg": next(iter(error)), "code": error.code} for error in _errors]
            for field, _errors in form.errors.as_data().items()
        }
        if form.is_bound
        else {}
    )

    values = {field.name: field.value() for field in form}
    return {
        "errors": errors,
        "values": values,
    }
