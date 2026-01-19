export interface TableButtonClickEvent {
  [key: string]: any
}

export interface TableSortEvent {
  value: string,
  order: 'asc' | 'desc'
}
