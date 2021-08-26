from django.db import models

from zac.elasticsearch.searches import search


class BoardItemQuerySet(models.QuerySet):
    def for_user(self, user) -> models.QuerySet:

        if user.is_superuser:
            return self

        zaak_urls = [item.object for item in self]
        allowed_zaak_documents = search(user=user, urls=zaak_urls)
        allowed_zaak_urls = [z.url for z in allowed_zaak_documents]

        return self.filter(object__in=allowed_zaak_urls)
