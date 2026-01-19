def get_zaaktype_response(catalogus: str, zaaktype: str, **kwargs) -> dict:
    response = {
        "url": zaaktype,
        "catalogus": catalogus,
        "identificatie": "12345",
        "omschrijving": "Main zaaktype",
        "omschrijvingGeneriek": "",
        "vertrouwelijkheidaanduiding": "openbaar",
        "doel": "some desc",
        "aanleiding": "some desc",
        "toelichting": "",
        "indicatieInternOfExtern": "intern",
        "handelingInitiator": "indienen",
        "onderwerp": "Klacht",
        "handelingBehandelaar": "uitvoeren",
        "doorlooptijd": "P30D",
        "servicenorm": None,
        "opschortingEnAanhoudingMogelijk": False,
        "verlengingMogelijk": False,
        "verlengingstermijn": None,
        "trefwoorden": ["qwerty"],
        "publicatieIndicatie": False,
        "publicatietekst": "",
        "verantwoordingsrelatie": ["qwerty"],
        "productenOfDiensten": ["https://example.com/product/123"],
        "selectielijstProcestype": (
            "https://selectielijst.openzaak.nl/api/v1/"
            "procestypen/e1b73b12-b2f6-4c4e-8929-94f84dd2a57d"
        ),
        "referentieproces": {},
        "statustypen": [],
        "resultaattypen": [],
        "eigenschappen": [],
        "informatieobjecttypen": [],
        "roltypen": [],
        "besluittypen": [],
        "deelzaaktypen": [],
        "gerelateerdeZaaktypen": [],
        "beginGeldigheid": "2019-11-20",
        "eindeGeldigheid": "2020-04-30",
        "versiedatum": "2019-11-20",
        "concept": False,
    }
    response.update(**kwargs)
    return response


def get_roltype_response(roltype: str, zaaktype: str, **kwargs):
    response = {
        "url": roltype,
        "zaaktype": zaaktype,
        "omschrijving": "some role",
        "omschrijvingGeneriek": "behandelaar",
    }
    response.update(**kwargs)
    return response
