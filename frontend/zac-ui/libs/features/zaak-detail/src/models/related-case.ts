export interface Zaaktype {
    url: string;
    catalogus: string;
    omschrijving: string;
    versiedatum: string;
  }

export interface Statustype {
  url: string;
  omschrijving: string;
  omschrijvingGeneriek: string;
  statustekst: string;
  volgnummer: number;
  isEindstatus: boolean;
}

export interface Status {
  url: string;
  datumStatusGezet: Date;
  statustoelichting: string;
  statustype: Statustype;
}

export interface Resultaat {
  resultaattype: {
    omschrijving: string;
    url: string;
  };
  toelichting: string;
  url: string;
}

export interface Zaak {
  url: string;
  identificatie: string;
  bronorganisatie: string;
  zaaktype: Zaaktype;
  omschrijving: string;
  toelichting: string;
  registratiedatum: string;
  startdatum: string;
  einddatum?: any;
  einddatumGepland?: any;
  uiterlijkeEinddatumAfdoening?: any;
  vertrouwelijkheidaanduiding: string;
  deadline: string;
  deadlineProgress: number;
  status: Status;
  resultaat?: any;
}

export interface RelatedCase {
  aardRelatie: string;
  zaak: Zaak;
}
