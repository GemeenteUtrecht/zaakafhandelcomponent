export interface MenuItem {
  id?: string;
  icon?: string;
  label: string;
  to: string;
  subs?: MenuItem[];
  marginBottom?: boolean;
}
