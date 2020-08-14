from django.db import models

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes


class CoreConfig(SingletonModel):
    primary_drc = models.ForeignKey(
        "zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.drc},
    )
