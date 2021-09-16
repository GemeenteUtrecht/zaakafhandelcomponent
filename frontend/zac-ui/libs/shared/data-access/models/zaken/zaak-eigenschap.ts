export interface Eigenschap {
  url: string;
  naam: string;
  toelichting: string;
  specificatie: Specificatie;
}

export interface EigenschapWaarde {
  eigenschap: Eigenschap;
  formaat: string;
  url: string;
  value: string;
}

export interface Specificatie {
  groep: string;
  formaat: string;
  lengte: string;
  kardinaliteit: string;
  waardenverzameling: string[];
}
