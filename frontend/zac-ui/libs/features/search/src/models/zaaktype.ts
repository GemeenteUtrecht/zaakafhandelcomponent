export interface Result {
  omschrijving: string;
  identificatie: string;
  catalogus: string;
  url: string;
}

export interface Zaaktype {
  count: number;
  next: string;
  previous: string;
  results: Result[];
}

