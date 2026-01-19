/**
 * This CreateBetrokkene interface is used to POST a new betrokkene to the API
 */

interface BetrokkeneIdentificatie {
  identificatie: string;
  naam?: string;
  isGehuisvestIn?: string;
}

export interface CreateBetrokkene {
  betrokkene?: string;
  betrokkeneType: string;
  indicatieMachtiging?: string;
  roltype: string;
  zaak: string;
  betrokkeneIdentificatie: BetrokkeneIdentificatie;
}
