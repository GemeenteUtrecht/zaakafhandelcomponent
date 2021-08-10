export interface Document {
  auteur: string;
  beschrijving: string;
  bestandsnaam: string;
  bestandsomvang: number;
  currentUserIsEditing: boolean;
  identificatie: string;
  informatieobjecttype: InformatieObjectType;
  locked: boolean;
  readUrl: string;
  title: string;
  url: string;
  vertrouwelijkheidaanduiding: string;
  versie: number,
  writeUrl: string;
}

export interface DocumentUrls {
  writeUrl?: string;
  deleteUrl?: string;
  drcUrl?: string;
  id?: string;
}

export interface ReadWriteDocument {
  magicUrl: string;
  deleteUrl: string;
  drcUrl: string;
  purpose: string;
}

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
