import { Dashboard, DashboardColumn } from './dashboard';

interface Zaaktype {
  url: string;
  catalogus: string;
  omschrijving: string;
}

interface BetrokkeneIdentificatie {
  identificatie: string;
}

interface Rollen {
  url: string;
  betrokkeneType: string;
  omschrijvingGeneriek: string;
  betrokkeneIdentificatie: BetrokkeneIdentificatie;
}

interface Eigenschappen {
  tekst: string;
  getal: string;
  datum: string;
  datumTijd: Date;
}

interface Status {
  url: string;
  statustype: string;
  datumStatusGezet: Date;
  statustoelichting: string;
}

interface Zaakobjecten {
  url: string;
  object: string;
}

interface Zaak {
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
  board: Dashboard;
  column: DashboardColumn;
  zaak: Zaak;
}
