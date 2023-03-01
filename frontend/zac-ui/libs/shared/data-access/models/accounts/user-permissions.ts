import {ZaakPermission} from "../zaken/zaak-permission";

export interface UserPermission {
  permissions: ZaakPermission[],
  username: string,
  fullName: string,
}
