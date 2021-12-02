export interface UserGroupResult {
  id: number;
  fullName: string;
  name: string;
}

export interface UserGroupList {
  count: number;
  next?: any;
  previous?: any;
  results: UserGroupResult[];
}
