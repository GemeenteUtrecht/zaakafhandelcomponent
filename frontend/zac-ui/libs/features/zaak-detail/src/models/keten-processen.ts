import { Task } from "@gu/models";

export interface Assignee {
  username: string;
  firstName: string;
  lastName: string;
  id: number;
}

export interface SubProcess {
  id: string;
  definitionId: string;
  title: string;
  subProcesses: SubProcess[];
  messages: any[];
  tasks: Task[];
}

export interface KetenProcessen {
  id: string;
  definitionId: string;
  title: string;
  subProcesses: SubProcess[];
  messages: string[];
  tasks: Task[];
}
