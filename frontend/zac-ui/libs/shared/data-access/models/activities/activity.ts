import {User} from '../accounts/user';

export interface Event {
  activity: number;
  created: string;
  createdBy: User
  id: number;
  notes: string;
}

export interface Activity {
  createdBy: User;
  id: number;
  url: string;
  zaak: string;
  name: string;
  remarks: string;
  status: 'on_going' | 'finished';
  userAssignee: {
    id: number;
    username: string;
    firstName: string
    fullName: string;
    lastName: string;
    isStaff: boolean;
    email: string;
    groups: string[];
  };
  groupAssignee: {
    id: number;
    name: string;
    fullName: string;
  };
  document: string;
  created: Date;
  events: Event[];
}
