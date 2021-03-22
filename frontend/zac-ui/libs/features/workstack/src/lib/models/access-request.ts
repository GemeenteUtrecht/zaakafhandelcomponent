export interface Request {
  requester: string;
}

export interface Zaak {
  identificatie: string;
  bronorganisatie: string;
  url: string;
}

export interface AccessRequests {
  accessRequests: Request[];
  url: string;
  zaak: Zaak;
}
