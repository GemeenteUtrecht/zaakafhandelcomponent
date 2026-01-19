from django.db import models

from zac.elasticsearch.searches import search_zaken


class BoardItemQuerySet(models.QuerySet):
    def for_user(self, request) -> models.QuerySet:

        if request.user and request.user.is_superuser:
            return self

        zaak_urls = [item.object for item in self]
        allowed_zaak_documents = search_zaken(
            request=request, urls=zaak_urls, size=len(zaak_urls)
        )
        allowed_zaak_urls = [z.url for z in allowed_zaak_documents]

        return self.filter(object__in=allowed_zaak_urls)
