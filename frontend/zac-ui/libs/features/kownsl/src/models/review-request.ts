import { Review } from './review';
import { ZaakDocument } from './zaak-document';
import { Zaak } from './zaak';
import {Approval} from "./approval";
import {Advice} from "./advice";
import {User, UserGroupDetail} from '@gu/models';

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
  forZaak: string;
  reviewType: string;
  documents: string[];
  frontendUrl: string;
  numAdvices: number;
  numApprovals: number;
  numAssignedUsers: number;
  toelichting: string;
  userDeadlines: any;
  requester: Requester;
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
  canLock: boolean;
  locked: boolean;
  lockReason: string;
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
