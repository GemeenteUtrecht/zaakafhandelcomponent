export interface Column {
  uuid: string;
  name: string;
  slug: string;
  order: number;
  created: Date;
  modified: Date;
}

export interface Zaaktype {
  url: string;
  catalogus: string;
  omschrijving: string;
}

export interface BetrokkeneIdentificatie {
  identificatie: string;
}

export interface Rollen {
  url: string;
  betrokkeneType: string;
  omschrijvingGeneriek: string;
  betrokkeneIdentificatie: BetrokkeneIdentificatie;
}

export interface Eigenschappen {
  tekst: string;
  getal: string;
  datum: string;
  datumTijd: Date;
}

export interface Status {
  url: string;
  statustype: string;
  datumStatusGezet: Date;
  statustoelichting: string;
}

export interface Zaakobjecten {
  url: string;
  object: string;
}

export interface Zaak {
  url: string;
  zaaktype: Zaaktype;
  identificatie: string;
  bronorganisatie: string;
  omschrijving: string;
  vertrouwelijkheidaanduiding: string;
  vaOrder: number;
  rollen: Rollen[];
  startdatum: Date;
  einddatum: Date;
  registratiedatum: Date;
  deadline: Date;
  eigenschappen: Eigenschappen[];
  status: Status;
  toelichting: string;
  zaakobjecten: Zaakobjecten[];
}

export interface BoardItem {
  url: string;
  uuid: string;
  objectType: string;
  object: string;
  board: string;
  column: Column;
  zaak: Zaak;
}
