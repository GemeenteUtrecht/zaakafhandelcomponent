export interface CreateCase {
  zaaktypeOmschrijving: string,
  zaaktypeCatalogus: string,
  zaakDetails: {
    omschrijving: string,
    toelichting?: string
  }
}
