export interface ShortDocument {
  bestandsgrootte: string;
  documentType: string;
  readUrl: string;
  titel: string;
  vertrouwelijkheidaanduiding: string;
}

interface InformatieObjectType {
  omschrijving: string;
  url: string;
}

export interface Document {
  auteur: string;
  beschrijving: string;
  bestandsnaam: string;
  bestandsomvang: number;
  identificatie: string;
  informatieobjecttype: InformatieObjectType;
  locked: boolean;
  readUrl: string;
  title: string;
  url: string;
  vertrouwelijkheidaanduiding: string;
  writeUrl: string;
}
