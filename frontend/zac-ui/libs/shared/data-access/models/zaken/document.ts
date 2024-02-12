export interface Document {
  auteur: string;
  beschrijving: string;
  bestandsnaam: string;
  bestandsomvang: number;
  currentUserIsEditing: boolean;
  deleteUrl: string,
  downloadUrl: string,
  identificatie: string;
  informatieobjecttype: InformatieObjectType;
  locked: boolean;
  lockedBy: string;
  readUrl: string;
  titel: string;
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

export interface InformatieObjectType {
  omschrijving: string;
  url: string;
}

export interface ListDocuments {
  count: number;
  fields: string[];
  next: string;
  previous: string;
  results: Document[];
}
