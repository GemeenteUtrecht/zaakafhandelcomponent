from dataclasses import dataclass
from .base import Model
from ..camel_case import underscoreize


# Can't inherit model because of id field
@dataclass
class ProcessInstance:
    id: str
    definition_id: str
    business_key: str
    case_instance_id: str
    ended: bool
    suspended: bool
    tenant_id: str

    @classmethod
    def from_raw(cls, raw_data: dict, strict=False):
        kwargs = underscoreize(raw_data)
        # strip out the unknown keys
        if not strict:
            known_keys = cls.__annotations__.keys()
            init_kwargs = {
                key: value
                for key, value
                in kwargs.items() if key in known_keys
            }
        else:
            init_kwargs = kwargs

        return cls(**init_kwargs)
