from typing import List

from furl import furl


def remote_schema_ref(url: str, fragment_parts: List[str]) -> dict:
    ref = furl("/api/_get-remote-schema/")
    ref.args["schema"] = url
    ref.fragment.path.segments = fragment_parts
    ref.fragment.path.isabsolute = True
    return {"$ref": ref.url}
