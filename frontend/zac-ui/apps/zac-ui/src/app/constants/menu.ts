import { MenuItem } from '@gu/models';

const menuItems: MenuItem[] = [
  {
    icon: 'article',
    label: 'Werkvoorraad',
    to: '/',
  },
  {
    icon: 'search',
    label: 'Zaken zoeken',
    to: '/zaken',
  },
];

const bottomMenuItems: MenuItem[] = [
  // {
  //   icon: 'login',
  //   label: 'Inloggen',
  //   to: '/accounts/login/?next=/ui/',
  //   external: true
  // },
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
