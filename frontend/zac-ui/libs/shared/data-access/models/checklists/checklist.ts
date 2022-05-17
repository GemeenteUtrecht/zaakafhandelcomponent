import {UserGroupDetail} from '../accounts/user-group';
import {User} from '../accounts/user';

export interface ChecklistAnswer {
  remarks: string;
  question: string,
  answer: string,
  created: string,
  document?: string
}

export interface Checklist {
  answers: ChecklistAnswer[],
  groupAssignee?: UserGroupDetail,
  userAssignee?: User,
  url?: string,
  created?: string,
}
