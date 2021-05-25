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
  omschrijving: string;
  startdatum: string;
  status: string;
  zaaktypeOmschrijving: string;
  eigenschappen: Eigenschappen[];
}

export interface ReportCases {
  count: number;
  next: string;
  previous: string;
  results: ReportCase[]
}
