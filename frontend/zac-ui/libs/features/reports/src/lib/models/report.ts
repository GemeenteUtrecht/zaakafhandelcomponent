import {EigenschapWaarde, Zaaktype} from '@gu/models';

export interface ReportType {
  id: number;
  name: string;
}

export interface Status {
  datumStatusGezet: string;
  statustoelichting: string;
  statustype: string;
}

export interface ReportCase {
  identificatie: string;
  bronorganisatie: string;
  omschrijving: string;
  toelichting: string;
  startdatum: string;
  status: Status;
  zaaktype: Zaaktype;
  eigenschappen: EigenschapWaarde[];
}

export interface ReportCases {
  count: number;
  next: string;
  previous: string;
  results: ReportCase[]
}
