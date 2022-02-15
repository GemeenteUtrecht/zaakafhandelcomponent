export interface HistoricalUserTaskData {
  assignee: {
    id: number,
    username: string,
    firstName: string,
    fullName: string,
    lastName: string,
    isStaff: true,
    email: string,
    groups: string[]
  },
  completed: string,
  created: string,
  name: string,
  history: HistoricalUserTaskDataItem[]
}

export interface HistoricalUserTaskDataItem {
  naam: string,
  waarde: any,
  label: string
}
