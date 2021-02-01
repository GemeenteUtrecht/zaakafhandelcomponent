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

interface InformatieObjectType {
  omschrijving: string;
  url: string;
}

export interface DocumentUrls {
  writeUrl: string;
  deleteUrl: string;
}

export interface ReadWriteDocument {
  magicUrl: string;
  deleteUrl: string;
  purpose: string;
}
