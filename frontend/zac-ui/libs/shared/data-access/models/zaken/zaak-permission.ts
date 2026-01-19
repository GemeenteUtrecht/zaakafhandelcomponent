export interface ZaakPermission {
  id: number,
  requester: string,
  permission: string,
  zaak: string,
  startDate: string,
  endDate?: string,
  comment?: string,
  reason: string,
}
