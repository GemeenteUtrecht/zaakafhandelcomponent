export interface UserSearchResult {
  id: number;
  username: string;
  fullName: string;
  firstName: string;
  lastName: string;
  isStaff: boolean;
  email: string;
  groups: string[];
}

export interface UserSearch {
  count: number;
  next?: any;
  previous?: any;
  results: UserSearchResult[];
}
