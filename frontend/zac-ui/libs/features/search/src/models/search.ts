export interface Zaaktype {
  omschrijving: string;
  catalogus: string;
}

export interface Eigenschappen {
  [key: string]: any
}

export interface Search {
  identificatie?: string;
  zaaktype?: Zaaktype;
  omschrijving?: string;
  eigenschappen?: Eigenschappen;
}
