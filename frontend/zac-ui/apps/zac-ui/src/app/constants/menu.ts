import { MenuItem } from '@gu/models';
import {getEnv} from '@gu/utils';

const menuItems: MenuItem[] = [
  {
    icon: 'home',
    label: 'Startpagina',
    to: '/',
  },
  {
    icon: 'inventory',
    label: 'Werkvoorraad',
    to: '/werkvoorraad',
  },
  {
    icon: 'search',
    label: 'Zoeken',
    to: '/zoeken',
  },
  {
    icon: 'feed',
    label: 'Zaak starten',
    to: '/zaak-starten',
  },
  {
    icon: 'dashboard',
    label: 'Dashboard',
    to: '/dashboard',
  },
  {
    icon: 'summarize',
    label: 'Rapportages',
    to: '/rapportages',
  },
  {
    icon: 'open_in_new',
    label: 'Tezza',
    to: getEnv('ALFRESCO_PREVIEW_URL', 'https://alfresco-tezza.cg-intern.ont.utrecht.nl/'),
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
