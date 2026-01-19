export interface ApprovalForm {
  approved: boolean | string;
  toelichting: string;
  zaakeigenschappen: {
    url: string,
    naam: string,
    waarde: string
  }[]
}
