export interface MetaZaaktypeResult {
  omschrijving: string;
  catalogus: string;
}

export interface MetaZaaktype {
  count: number;
  next: string;
  previous: string;
  results: MetaZaaktypeResult[];
}

