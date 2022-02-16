export interface Activity {
  name: string;
  groupAssignee: string;
  userAssignee: string;
}

export interface Zaak {
  identificatie: string;
  bronorganisatie: string;
  url: string;
}

export interface AdHocActivities {
  activities: Activity[];
  url: string;
  zaak: Zaak;
}

