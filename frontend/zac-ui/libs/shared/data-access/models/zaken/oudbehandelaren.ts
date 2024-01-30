import { User } from '../accounts/user';

export interface Oudbehandelaar {
  email: string
  ended: string
  started: string
  user: User
}

export interface Oudbehandelaren {
  zaak: string,
  oudbehandelaren: Oudbehandelaar[];
}
