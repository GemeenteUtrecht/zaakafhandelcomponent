import { AuthProfile } from './auth-profile';
import { User } from './user';

export interface UserAuthProfile {
  start: Date;
  end?: any;
  id: number;
  user: User;
  authProfile: AuthProfile;
}

export interface UserAuthProfiles {
  count: number;
  next?: any;
  previous?: any;
  results: UserAuthProfile[];
}

