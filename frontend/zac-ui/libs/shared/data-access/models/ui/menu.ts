export interface MenuItem {
  id?: string;
  icon?: string;
  label: string;
  to: string;
  external?: boolean;
  subs?: MenuItem[];
  marginBottom?: boolean;
  adminOnly?: boolean;
}
