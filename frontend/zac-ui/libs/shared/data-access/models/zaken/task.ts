import { Assignee } from './assignee';
import { Zaak } from './zaak';

export interface Task {
  id: string;
  executeUrl: string;
  name: string;
  created: Date;
  hasForm: boolean;
  assignee: Assignee;
  assigneeType: 'user' | 'group';
  canCancelTask: boolean;
  formKey: string;
}

export interface UserTask {
  task: string;
  zaak: Zaak;
}
