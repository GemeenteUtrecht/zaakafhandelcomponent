import { Author } from './author';

export interface Review {
  advice?: string;
  toelichting?: string;
  approved?: boolean;
  author: Author;
  created: string;
}
