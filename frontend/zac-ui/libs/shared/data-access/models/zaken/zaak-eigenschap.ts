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
  waarde: string;
  naam?: string;
}

export interface NieuweEigenschap {
  naam: string;
  waarde: string;
  zaakUrl: string;
}

export interface Specificatie {
  groep: string;
  formaat: string;
  lengte: string;
  kardinaliteit: string;
  waardenverzameling: string[];
}
