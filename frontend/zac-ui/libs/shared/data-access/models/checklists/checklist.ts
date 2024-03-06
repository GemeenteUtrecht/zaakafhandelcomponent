import {UserGroupDetail} from '../accounts/user-group';
import {User} from '../accounts/user';

export interface ChecklistAnswer {
  remarks: string;
  question: string,
  answer: string,
  document?: string
  groupAssignee?: UserGroupDetail,
  userAssignee?: User,
}

export interface Checklist {
  answers: ChecklistAnswer[],
  url?: string,
}
