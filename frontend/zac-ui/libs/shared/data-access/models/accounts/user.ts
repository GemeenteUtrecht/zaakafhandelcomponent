export interface User {
  id: number;
  username: string;
  firstName: string;
  fullName: string;
  lastName: string;
  isStaff: boolean;
  email: string;
  groups: string[];
}
