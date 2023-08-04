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
    component: 'reviews',
    label: 'Advies/akkoord',
    endpoint: '/api/workstack/review-requests'
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
  'reviews': 3,
  'activities': 4,
  'group-activities': 5,
  'access-request': 6,
  'checklist': 7,
  'group-checklist': 8
}

export { tabs, tabIndexes }
