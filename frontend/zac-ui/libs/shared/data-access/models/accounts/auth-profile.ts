enum MaxVertrouwelijkheidsAanduiding {
  openbaar = "openbaar",
  beperkt_openbaar = "beperkt_openbaar",
  intern = "intern",
  zaakvertrouwelijk = "zaakvertrouwelijk",
  vertrouwelijk = "vertrouwelijk",
  confidentieel = "confidentieel",
  geheim = "geheim",
  zeer_geheim = "zeer_geheim"
}

// Zaak
export interface ZaakPolicy {
  catalogus: string;
  zaaktypeOmschrijving: string;
  maxVa: MaxVertrouwelijkheidsAanduiding;
}

// Document
interface DocumentPolicy {
  catalogus: string;
  iotypeOmschrijving: string;
  maxVa: MaxVertrouwelijkheidsAanduiding;
}

// Search report
interface SearchReportPolicy {
  zaaktype: string[];
}

/**
 * Generic interfaces
 */
export interface BlueprintPermission {
  role: number;
  objectType: 'zaak' | 'document' | 'search_report';
  policies: ZaakPolicy[] | DocumentPolicy[] | SearchReportPolicy[];
}

export interface AuthProfile {
  url: string;
  uuid: string;
  name: string;
  blueprintPermissions: BlueprintPermission[];
}
