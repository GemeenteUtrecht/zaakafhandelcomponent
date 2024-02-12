export interface AssignedUser {
  users: string[];
  deadline: string;
}

export interface AssignUsersForm {
  form: string;
  assignedUsers: AssignedUser[];
  documents: string[];
  toelichting: string;
}
