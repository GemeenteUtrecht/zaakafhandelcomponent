export interface RecentlyViewed {
  "visited": Date,
  "identificatie": string,
  "url": string
}

export interface RecentlyViewedCases {
  recentlyViewed: RecentlyViewed[]
}
