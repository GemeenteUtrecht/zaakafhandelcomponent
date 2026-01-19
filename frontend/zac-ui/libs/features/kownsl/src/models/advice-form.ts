export interface AdviceForm {
  advice: string;
  reviewDocuments: ReviewDocument[] | [];
  zaakeigenschappen: {
    url: string,
    naam: string,
    waarde: string
  }[]
}

export interface ReviewDocument {
  document: string;
  editedDocument?: string;
}
