def get_paginated_results(client, resource: str, *args, **kwargs) -> list:
    initial = client.list(resource, *args, **kwargs)
    if not initial["next"]:
        return initial["results"]
    else:
        raise NotImplementedError
