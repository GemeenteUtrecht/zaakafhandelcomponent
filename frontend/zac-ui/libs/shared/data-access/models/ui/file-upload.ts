export interface FileUpload {
  content: string | ArrayBuffer;
  size: number; // kb
  name: string;
  document: string;
}
