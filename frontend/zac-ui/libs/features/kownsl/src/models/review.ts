import { Author } from './author';

export interface Document {
  document: string;
  sourceVersion: number;
  adviceVersion: number;
}

export interface Review {
  advice?: string;
  toelichting?: string;
  approved?: boolean;
  author: Author;
  created: string;
  documents: Document[];
}
