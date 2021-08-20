import {Author} from "./author";

export interface Advice {
  author: Author,
  created: string,
  status: 'Akkoord' | 'Niet akkoord',
  toelichting: string,
}
