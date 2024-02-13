export interface AdviceForm {
  advice: string;
  adviceDocuments: AdviceDocument[] | [];
}

export interface AdviceDocument {
  document: string;
  editedDocument: string;
}
