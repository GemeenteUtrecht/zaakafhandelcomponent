export interface Tab {
  component: string;
  label: string;
  endpoint: string;
}

const tabs: Tab[] = [
  {
    component: 'zaken',
    label: 'In behandeling',
    endpoint: '/api/workstack/cases'
  },
  {
    component: 'tasks',
    label: 'Taken',
    endpoint: '/api/workstack/user-tasks'
  },
  {
    component: 'group-tasks',
    label: 'Taken gebruikersgroepen',
    endpoint: '/api/workstack/group-tasks'
  },
  {
    component: 'activities',
    label: 'Zaakactiviteiten',
    endpoint: '/api/workstack/activities'
  },
  {
    component: 'access-request',
    label: 'Toegangsverzoeken',
    endpoint: '/api/workstack/access-requests'
  },
];

export { tabs }
