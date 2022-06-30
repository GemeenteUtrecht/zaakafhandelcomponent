export interface BetrokkeneIdentificatie {
  identificatie: string;
  naam: string;
  isGehuisvestIn: string;
}

export interface Betrokkene {
  betrokkene?: string;
  betrokkeneType: string;
  indicatieMachtiging: string;
  roltype: string;
  zaak: string;
  betrokkeneIdentificatie: any;
}
