export interface ChecklistQuestion {
  question: string;
  groupAssignee: string;
  userAssignee: string;
}

export interface Status {
  url: string;
  statustype: string;
  datumStatusGezet: Date;
  statustoelichting: string;
}

export interface Zaak {
  url: string;
  identificatie: string;
  bronorganisatie: string;
  status: Status;
}

export interface WorkstackChecklist {
  checklistQuestions: ChecklistQuestion[];
  zaak: Zaak;
}
