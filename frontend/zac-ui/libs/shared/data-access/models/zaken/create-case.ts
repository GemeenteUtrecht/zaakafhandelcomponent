export interface CreateCase {
  zaaktypeIdentificatie: string,
  zaaktypeCatalogus: string,
  zaakDetails: {
    omschrijving: string,
    toelichting?: string
  },
  start_related_business_process: boolean
}
