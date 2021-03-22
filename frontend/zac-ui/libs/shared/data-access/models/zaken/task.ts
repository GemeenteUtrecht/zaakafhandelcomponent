import { Assignee } from './assignee';

export interface Task {
  id: string;
  executeUrl: string;
  name: string;
  created: string;
  hasForm: boolean;
  assignee: Assignee;
}
