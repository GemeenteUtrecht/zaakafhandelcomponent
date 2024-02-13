import { Review } from './review';
import { Zaak } from './zaak';
import {Approval} from "./approval";
import {Advice} from "./advice";
import {Document, User, UserGroupDetail} from '@gu/models';

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
  zaakeigenschappen: any[];
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
