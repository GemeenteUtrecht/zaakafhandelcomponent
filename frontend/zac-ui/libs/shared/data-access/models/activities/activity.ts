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
  assignee?: number;
  document: string;
  created: Date;
  events: Event[];
}
