export interface Result {
  id: number;
  username: string;
  firstName: string;
  lastName: string;
  isStaff: boolean;
  email: string;
  name?: string;
}

export interface UserSearch {
  count: number;
  next?: any;
  previous?: any;
  results: Result[];
}
