import { Review } from './review';
import { ZaakDocument } from './zaak-document';

export interface ReviewRequest {
  created: string;
  documents: string[];
  review_type: string;
  reviews: Review[];
  toelichting: string;
  zaak_documents: ZaakDocument[];
}
