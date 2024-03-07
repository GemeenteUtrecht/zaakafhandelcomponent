import { EigenschapWaarde, Task } from '@gu/models';

export interface Document {
  beschrijving: string;
  bestandsnaam: string;
  bestandsomvang?: number;
  url: string;
  readUrl: string;
  versie?: number;
  documentType?: string;
}

export interface ZaakInformatie {
  omschrijving: string;
  toelichting: string;
}

export interface FormField {
  name: string;
  label: string;
  inputType: 'enum' | 'string' | 'int' | 'boolean' | 'date';
  value: string | number | boolean;
  enum?: Array<string[]>;
  spec: {
    maxLength?: number;
    minLength?: number;
    type: string;
  }
}

interface InformatieObjectType {
  omschrijving: string;
  url: string;
}

export interface BenodigdeBijlage {
  alreadyUploadedInformatieobjecten: string[];
  allowMultiple: boolean;
  informatieobjecttype: InformatieObjectType;
  label: string;
  required: boolean;
  order: number;
}

interface Roltype {
  url: string;
  omschrijving: string;
  omschrijvingGeneriek: string;
}

export interface BenodigdeRol {
  betrokkeneType: string;
  label: string;
  roltype: Roltype;
  required: boolean;
  order: number;
}

interface Specificatie {
  groep: string,
  formaat: string,
  lengte: string,
  kardinaliteit: string,
  waardenverzameling: string[]
}

interface Eigenschap {
  url: string;
  naam: string;
  toelichting: string;
  specificatie: Specificatie;
}

export interface Choice {
  label: string,
  value: string | number | object,
}


export interface BenodigdeZaakeigenschap {
  choices: Choice[],
  eigenschap: Eigenschap;
  label: string;
  default: string;
  required: boolean;
  order: number;
}

export interface Assignee {
  id: number,
  name: string,
  fullName: string,
  username: string
}

export interface AssignedUsers {
  userAssignees: Assignee[],
  groupAssignees: Assignee[]
}

export interface PreviouslyAssignedUser {
  deadline: string,
  emailNotification: boolean,
  groupAssignees: Assignee[],
  userAssignees: Assignee[]
}

export interface Context {
  id: string,
  camundaAssignedUsers: AssignedUsers;
  previouslyAssignedUsers: PreviouslyAssignedUser[];
  previouslySelectedDocuments: string[];
  previouslySelectedZaakeigenschappen: string[];
  documentsLink?: string;
  informatieobjecttypen?: InformatieObjectType[];
  title?: string;
  zaakInformatie?: ZaakInformatie;
  zaakeigenschappen?: EigenschapWaarde[];
  reviewType?: 'advice' | 'approval';
  formFields?: FormField[],
  redirectTo?: string,
  openInNewWindow?: boolean,
  benodigdeBijlagen?: BenodigdeBijlage[],
  benodigdeRollen?: BenodigdeRol[],
  benodigdeZaakeigenschappen?: BenodigdeZaakeigenschap[],
  activiteiten: any[],
  checklistVragen: any[],
  resultaattypen: any[],
  taken: any[],
  verzoeken: any[]
}

export interface TaskContextData {
  context: Context;
  form: 'zac:configureAdviceRequest' |
    'zac:configureApprovalRequest' |
    'zac:documentSelectie' |
    'zac:gebruikerSelectie' |
    'zac:validSign:configurePackage' |
    'zac:doRedirect' |
    any;
  task: Task;
}
