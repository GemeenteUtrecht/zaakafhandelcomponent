export interface Event {
  activity: number;
  created: string;
  id: number;
  notes: string;
}

export interface Activity {
  id: number;
  url: string;
  zaak: string;
  name: string;
  remarks: string;
  status: 'on_going' | 'finished';
  userAssignee: string;
  groupAssignee: string;
  document: string;
  created: Date;
  events: Event[];
}
