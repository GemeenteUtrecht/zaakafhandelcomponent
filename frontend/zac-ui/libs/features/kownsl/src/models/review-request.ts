import { Review } from './review';
import { ZaakDocument } from './zaak-document';

export interface ReviewRequest {
  created: string;
  documents: string[];
  reviewType: string;
  reviews: Review[];
  toelichting: string;
  zaakDocuments: ZaakDocument[];
}
