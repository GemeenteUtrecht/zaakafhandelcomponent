import { Review } from './review';
import { ZaakDocument } from './zaak-document';
import { Zaak } from './zaak';
import {Approval} from "./approval";
import {Advice} from "./advice";

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

export interface ReviewRequestSummary {
  id: string,
  reviewType: 'advice' | 'approval',
  completed: number,
  numAssignedUsers: number,
}

export interface ReviewRequestDetails {
  id: string,
  reviewType: string,
  approvals?: Approval[]
  advices?: Advice[]
}
