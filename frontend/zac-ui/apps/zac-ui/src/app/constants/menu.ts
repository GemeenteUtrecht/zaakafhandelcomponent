import { MenuItem } from '@gu/models';
import {isTestEnvironment} from "@gu/utils";

const menuItems: MenuItem[] = [
  {
    icon: 'inventory',
    label: 'Werkvoorraad',
    to: '/',
  },
  {
    icon: 'dashboard',
    label: 'Dashboard',
    to: '/dashboard',
  },
  {
    icon: 'search',
    label: 'Zoeken',
    to: '/zoeken',
  },
  {
    icon: 'feed',
    label: 'Formulieren',
    to: '/formulieren',
  },
  {
    icon: 'summarize',
    label: 'Rapportages',
    to: '/rapportages',
  },
  {
    icon: 'open_in_new',
    label: 'Alfresco',
    to: isTestEnvironment() ? 'https://alfresco-tezza.cg-intern.ont.utrecht.nl/' : 'https://alfresco-tezza.cg-intern.acc.utrecht.nl/',
    external: true,
    adminOnly: false,
  },
  {
    icon: 'manage_accounts',
    label: 'Autorisaties',
    to: '/autorisaties',
    adminOnly: true,
  },
  {
    icon: 'admin_panel_settings',
    label: 'Admin',
    to: '/admin',
    external: true,
    adminOnly: true,
  },
];
export { MenuItem, menuItems };
