from zgw_consumers.api_models.base import Model


@dataclass
class DocRequest(Model):
    purpose: str
    uuid: str
    drc_url: str
