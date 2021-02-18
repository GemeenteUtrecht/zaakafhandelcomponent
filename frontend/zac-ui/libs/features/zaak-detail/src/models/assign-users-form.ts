export interface AssignedUser {
  users: string[];
  deadline: string;
}

export interface AssignUsersForm {
  form: string;
  assignedUsers: AssignedUser[];
  selectedDocuments: string[];
  toelichting: string;
}
