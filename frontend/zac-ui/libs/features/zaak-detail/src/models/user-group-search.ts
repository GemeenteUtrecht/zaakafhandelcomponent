import {UserGroupDetail} from '@gu/models';

export interface UserGroupList {
  count: number;
  next?: any;
  previous?: any;
  results: UserGroupDetail[];
}
