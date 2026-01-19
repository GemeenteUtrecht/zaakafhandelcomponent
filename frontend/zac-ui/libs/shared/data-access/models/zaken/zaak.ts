import {Geometry} from "../geojson/geojson";

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

export interface WorkstackStatus {
  url: string;
  datumStatusGezet: Date;
  statustoelichting: string;
  statustype: string;
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
  status: Status;
  zaakgeometrie: Geometry;
  kanGeforceerdBijwerken: boolean;
  isStatic: boolean;
  hasProcess: boolean;
  isConfigured: boolean;
}

export interface WorkstackCase {
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
  status: WorkstackStatus;
  zaakgeometrie: Geometry;

}

