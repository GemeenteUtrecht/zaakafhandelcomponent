import { Assignee } from './assignee';

export interface UserTaskZaak {
  bronorganisatie: string;
  identificatie: string;
  url: string;
}

export interface Task {
  id: string;
  executeUrl: string;
  name: string;
  created: Date;
  hasForm: boolean;
  assignee: Assignee;
}

export interface UserTask {
  task: Task;
  zaak: UserTaskZaak;
}
