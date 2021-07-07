export interface Permission {
  "id": number,
  "requester": string,
  "permission": string,
  "zaak": string,
  "startDate": string,
  "endDate?": string,
  "comment?": string,
  "reason": string,
}

export interface UserPermission {
  permissions: Permission[],
  username: string,
}
