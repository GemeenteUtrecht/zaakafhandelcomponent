import {Permission} from "../zaken/permission";

export interface UserPermission {
  permissions: Permission[],
  username: string,
}
