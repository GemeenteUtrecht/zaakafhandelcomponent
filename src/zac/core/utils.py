def get_paginated_results(client, resource: str, min=25, *args, **kwargs) -> list:
    initial = client.list(resource, *args, **kwargs)
    if not initial["next"] or len(initial["results"]) >= min:
        return initial["results"]
    else:
        raise NotImplementedError
