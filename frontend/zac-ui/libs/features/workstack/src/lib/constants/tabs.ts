export interface Tab {
  component: string;
  label: string;
  endpoint: string;
}

const tabs: Tab[] = [
  {
    component: 'zaken',
    label: 'Zaken (behandelaar)',
    endpoint: '/api/workstack/cases?ordering=-deadline'
  },
  {
    component: 'tasks',
    label: 'Taken (proces)',
    endpoint: '/api/workstack/user-tasks'
  },
  {
    component: 'activities',
    label: 'Ad-hoc-activiteiten',
    endpoint: '/api/workstack/activities'
  },
  {
    component: 'access-request',
    label: 'Toegangsverzoeken',
    endpoint: '/api/workstack/access-requests'
  },
];

export { tabs }
