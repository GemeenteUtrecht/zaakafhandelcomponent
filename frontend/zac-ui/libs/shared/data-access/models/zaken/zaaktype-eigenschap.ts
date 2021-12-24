export interface Spec {
  type: string;
  format?: string;
  minLength?: number;
  maxLength?: number;
  enum?: any[];
}

export interface ZaaktypeEigenschap {
  url: string;
  name: string;
  spec: Spec;
}
