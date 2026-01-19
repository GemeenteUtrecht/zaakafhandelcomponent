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
  approved?: boolean;
  advice?: string;
  toelichting?: string;
  reviewDocuments?: ReviewDocument[];
}

export interface ReviewDocument {
  bestandsnaam: string;
  document: string;
  downloadReviewUrl: string;
  downloadSourceUrl: string;
  reviewUrl: string;
  reviewVersion: number;
  sourceUrl: string;
  sourceVersion: number;
}
