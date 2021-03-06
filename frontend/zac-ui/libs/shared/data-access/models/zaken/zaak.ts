export interface Zaaktype {
  url: string;
  catalogus: string;
  omschrijving: string;
  versiedatum: string;
}

export interface Resultaattype {
  url: string;
  omschrijving: string;
}

export interface Resultaat {
  url: string;
  resultaattype: Resultaattype;
  toelichting: string;
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
  einddatum?: string;
  einddatumGepland?: string;
  uiterlijkeEinddatumAfdoening?: string;
  vertrouwelijkheidaanduiding: string;
  deadline: string;
  deadlineProgress: number;
  resultaat: Resultaat;
}
