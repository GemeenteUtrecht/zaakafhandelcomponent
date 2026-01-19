export interface DashboardColumn {
  uuid: string;
  name: string;
  slug: string;
  order: number;
  created: Date;
  modified: Date;
}

export interface Dashboard {
  url: string;
  uuid: string;
  name: string;
  slug: string;
  created: Date;
  modified: Date;
  columns: DashboardColumn[];
}
