import { Zaaktype } from '@gu/models';

export interface ReportType {
  id: number;
  name: string;
}

export interface Specificatie {
  groep: string;
  formaat: string;
  lengte: string;
  kardinaliteit: string;
  waardenverzameling: string[];
}

export interface Eigenschap {
  url: string;
  naam: string;
  toelichting: string;
  specificatie: Specificatie;
}

export interface Eigenschappen {
  url: string;
  formaat: string;
  eigenschap: Eigenschap;
  value: Date;
}

export interface ReportCase {
  identificatie: string;
  bronorganisatie: string;
  omschrijving: string;
  toelichting: string;
  startdatum: string;
  status: string;
  zaaktype: Zaaktype;
  eigenschappen: Eigenschappen[];
}

export interface ReportCases {
  count: number;
  next: string;
  previous: string;
  results: ReportCase[]
}
