export interface RecentlyViewed {
  "visited": Date,
  "identificatie": string,
  "url": string,
  "omschrijving": string,
  "zaaktypeOmschrijving": string
}

export interface RecentlyViewedCases {
  recentlyViewed: RecentlyViewed[]
}
