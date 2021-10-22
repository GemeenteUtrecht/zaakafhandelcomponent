export interface Column {
  uuid: string;
  name: string;
  slug: string;
  order: number;
  created: Date;
  modified: Date;
}

export interface Board {
  url: string;
  uuid: string;
  name: string;
  slug: string;
  created: Date;
  modified: Date;
  columns: Column[];
}
