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
    label: 'Activiteiten',
    endpoint: '/api/workstack/activities'
  },
  {
    component: 'group-activities',
    label: 'Groepsactiviteiten',
    endpoint: '/api/workstack/group-activities'
  },
  {
    component: 'access-request',
    label: 'Toegangsverzoeken',
    endpoint: '/api/workstack/access-requests'
  },
  {
    component: 'checklist',
    label: 'Checklist',
    endpoint: '/api/workstack/checklists'
  },
  {
    component: 'group-checklist',
    label: 'Groepschecklist',
    endpoint: '/api/workstack/group-checklists'
  },
];


const tabIndexes = {
  'zaken': 0,
  'tasks': 1,
  'group-tasks': 2,
  'activities': 3,
  'group-activities': 4,
  'access-request': 5,
  'checklist': 6,
  'group-checklist': 7
}

export { tabs, tabIndexes }
