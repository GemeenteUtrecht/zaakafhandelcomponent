export interface HistoricalUserTaskData {
  assignee: string,
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
