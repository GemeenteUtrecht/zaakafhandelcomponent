import { Review } from './review';
import { Zaak } from './zaak';
import {Approval} from "./approval";
import {Advice} from "./advice";
import { Document, EigenschapWaarde, User, UserGroupDetail, ZaaktypeEigenschap } from '@gu/models';

export interface Metadata {
  taskDefinitionId: string;
  processInstanceId: string;
}

export interface Requester {
  username: string,
  firstName: string,
  lastName: string,
  fullName: string,
}

export interface ReviewRequest {
  created: Date;
  id: string;
  reviewType: string;
  documents: string[];
  frontendUrl: string;
  numAssignedUsers: number;
  toelichting: string;
  requester: Requester;
  metadata: Metadata;
  zaak: Zaak;
  zaakDocuments: Document[];
  zaakeigenschappen: EigenschapWaarde[];
  approvals?: Review[];
  advices?: Review[];
}

export interface ReviewRequestSummary {
  id: string,
  reviewType: 'advice' | 'approval',
  completed: number,
  numAssignedUsers: number,
  canLock: boolean;
  locked: boolean;
  lockReason: string;
  status: "approved" | "not_approved" | "pending" | "canceled" | "completed"
}

export interface OpenReview {
  deadline: Date,
  users: User[],
  groups: UserGroupDetail[]
}

export interface ReviewRequestDetails {
  id: string,
  reviewType: string,
  approvals?: Approval[],
  advices?: Advice[],
  openReviews: OpenReview[],
  isBeingReconfigured: boolean
}
