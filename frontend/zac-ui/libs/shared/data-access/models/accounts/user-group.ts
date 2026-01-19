import { User } from './user';

export interface UserGroupDetail {
  id: number;
  name: string;
  fullName: string;
  users?: User[];
}
