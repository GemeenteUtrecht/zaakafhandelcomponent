import {Author} from "./author";

export interface Approval {
  author: Author,
  created: string,
  status: 'Akkoord' | 'Niet akkoord',
  toelichting: string,
}
