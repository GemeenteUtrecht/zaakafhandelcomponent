export interface Document {
  beschrijving: string;
  bestandsnaam: string;
  bestandsomvang?: number;
  url: string;
  readUrl: string;
  versie?: number;
}

export interface ZaakInformatie {
  omschrijving: string;
  toelichting: string;
}

export interface Assignee {
  username: string;
  firstName: string;
  lastName: string;
  id: number;
}

export interface Task {
  id: string;
  executeUrl: string;
  name: string;
  created: Date;
  hasForm: boolean;
  assignee: Assignee;
}

export interface FormField {
  name: string;
  label: string;
  inputType: any;
  value: 0
}

export interface Context {
  documents: Document[];
  title?: string;
  zaakInformatie?: ZaakInformatie;
  reviewType?: 'advice' | 'approval';
  formFields?: FormField[]
}

export interface DocumentSelectie {
  documents: Document[]
}

export interface ValidSign {
  documents: Document[]
}

export interface TaskContextData {
  context: Context;
  form: 'zac:configureAdviceRequest' |
    'zac:configureApprovalRequest' |
    'zac:documentSelectie' |
    'zac:gebruikerSelectie' |
    'zac:validSign:configurePackage' |
    '';
  task: Task;
}
