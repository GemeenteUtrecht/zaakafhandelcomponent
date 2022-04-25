export interface ReviewDetail {
  id: string;
  reviewType: 'approval' | 'advice';
  approvals?: any;
  advices?: any;
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
  adviceUrl: string;
  adviceVersion: number;
  sourceUrl: string;
  sourceVersion: number;
  title: string;
}
