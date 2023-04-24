export interface RecentlyViewed {
  "visited": Date,
  "identificatie": string,
  "bronorganisatie": string
}

export interface RecentlyViewedCases {
  recentlyViewed: RecentlyViewed[]
}
