export interface AdviceForm {
  advice: string;
  documents: AdviceDocument[] | []
}

export interface AdviceDocument {
  content: string | ArrayBuffer;
  size: number;
  name: string;
  document: string;
}
