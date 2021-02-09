export interface ReviewDetail {
  id: string;
  reviewType: 'approval' | 'advice';
  reviews: any;
}

export interface Review {
  author: {
    firstName: string;
    lastName: string;
    username: string;
  };
  created: string;
  status?: 'Akkoord' | 'Niet akkoord';
  advice?: string;
  toelichting?: string;
  documents?: ReviewDocument[];
}

export interface ReviewDocument {
  adviceVersion: number;
  document: string;
  sourceVersion: number;
}
