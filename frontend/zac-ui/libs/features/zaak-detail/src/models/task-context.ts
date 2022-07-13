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

export interface BenodigdeBijlage {
  alreadyUploadedInformatieobjecten: string[];
  allowMultiple: boolean;
  informatieobjecttype: InformatieObjectType;
  label: string;
  required: boolean;
}

interface Roltype {
  url: string;
  omschrijving: string;
  omschrijvingGeneriek: string;
}

export interface BenodigdeRol {
  betrokkeneType: string;
  choices: Choice[];
  label: string;
  roltype: Roltype;
  required: boolean;
}

interface Specificatie {
  specificatie: {
    groep: string,
    formaat: string,
    lengte: string,
    kardinaliteit: string,
    waardenverzameling: string[]
  }
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
}

export interface Context {
  documents?: Document[];
  informatieobjecttypen?: InformatieObjectType[];
  title?: string;
  zaakInformatie?: ZaakInformatie;
  reviewType?: 'advice' | 'approval';
  formFields?: FormField[],
  redirectTo?: string,
  openInNewWindow?: boolean,
  benodigdeBijlagen?: BenodigdeBijlage[],
  benodigdeRollen?: BenodigdeRol[],
  benodigdeZaakeigenschappen?: BenodigdeZaakeigenschap[]
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
