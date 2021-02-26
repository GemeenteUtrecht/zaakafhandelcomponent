export interface AdviceForm {
  advice: string;
  documents: AdviceDocument[] | []
}

export interface AdviceDocument {
  document: string;
}
