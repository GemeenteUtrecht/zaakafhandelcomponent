import { MenuItem } from '@gu/models';

const menuItems: MenuItem[] = [
  {
    icon: 'search',
    label: 'Zoeken',
    to: '/zoeken',
    marginBottom: true,
  },
  {
    icon: 'article',
    label: 'Werkvoorraad',
    to: '/kownsl',
  },
  {
    icon: 'list',
    label: 'Alle zaken',
    to: '/zaken/002220647/ZAAK-2020-0000004839',
  },
];

const bottomMenuItems: MenuItem[] = [
  {
    icon: 'login',
    label: 'Inloggen',
    to: '/accounts/login/?next=/ui/',
    external: true
  },
  {
    icon: 'admin_panel_settings',
    label: 'Autorisatieprofielen',
    to: '/accounts/auth-profiles/',
    external: true,
    // roles: [UserRole.Admin],
  },
  {
    icon: 'admin',
    label: 'Admin',
    to: '/admin',
    external: true
    // roles: [UserRole.Admin],
  },
];
export { MenuItem, menuItems, bottomMenuItems };
