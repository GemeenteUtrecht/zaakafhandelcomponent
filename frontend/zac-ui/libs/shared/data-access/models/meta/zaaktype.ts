export interface Result {
  omschrijving: string;
  identificatie: string;
  catalogus: string;
}

export interface MetaZaaktype {
  count: number;
  next: string;
  previous: string;
  results: Result[];
}

