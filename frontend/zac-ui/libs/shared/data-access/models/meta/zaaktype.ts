export interface MetaZaaktypeCatalogus {
  domein: string,
  url: string
}

export interface MetaZaaktypeResult {
  omschrijving: string;
  catalogus: MetaZaaktypeCatalogus;
}

export interface MetaZaaktype {
  count: number;
  next: string;
  previous: string;
  results: MetaZaaktypeResult[];
}

