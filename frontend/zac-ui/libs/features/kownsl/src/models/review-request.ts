import { Review } from './review';
import { ZaakDocument } from './zaak-document';
import { Zaak } from './zaak';

export interface Metadata {
  taskDefinitionId: string;
  processInstanceId: string;
}

export interface ReviewRequest {
  created: Date;
  id: string;
  forZaak: string;
  reviewType: string;
  documents: string[];
  frontendUrl: string;
  numAdvices: number;
  numApprovals: number;
  numAssignedUsers: number;
  toelichting: string;
  userDeadlines: any;
  requester: string;
  metadata: Metadata;
  zaakDocuments: ZaakDocument[];
  reviews: Review[];
  zaak: Zaak;
}

