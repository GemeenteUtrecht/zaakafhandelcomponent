"""
Datamodels for ZGW resources.

These are NOT django models.
"""
from ..camel_case import underscoreize


class Model:

    @property
    def id(self):
        """
        Because of the usage of UUID4, we can rely on the UUID as identifier.
        """
        return self.url.split('/')[-1]

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
