import { Task } from '@gu/models';

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
}

interface InformatieObjectType {
  omschrijving: string;
  url: string;
}

export interface Context {
  documents?: Document[];
  informatieobjecttypen?: InformatieObjectType[];
  title?: string;
  zaakInformatie?: ZaakInformatie;
  reviewType?: 'advice' | 'approval';
  formFields?: FormField[],
  redirectTo?: string,
  openInNewWindow?: boolean
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
