export interface WorkstackReview {
  id: string
  reviewType: string
  openReviews: OpenReview[]
  isBeingReconfigured: boolean
  completed: number
  zaak: WorkstackReviewZaak
  advices?: WorkstackAdvice[]
  approvals?: WorkstackApproval[]
}

interface OpenReview {
  deadline: string
  users: User[]
  groups: Group[]
}

interface User {
  fullName: string
}

interface Group {
  name: string
}

interface WorkstackReviewZaak {
  url: string
  identificatie: string
  bronorganisatie: string
  status: Status
  zaaktype: Zaaktype
  omschrijving: string
  deadline: string
}

interface Status {
  url: string,
  statustype: string,
  datumStatusGezet: Date,
  statustoelichting: string
}

interface Zaaktype {
  url: string
  catalogus: string
  omschrijving: string
  identificatie: string
}

export interface WorkstackAdvice {
  created: string
  author: Author
  advice: string
  group: string
}

export interface WorkstackApproval {
  created: string
  author: Author
  status: string
  toelichting: string
  group: string
}

interface Author {
  firstName: string
  lastName: string
  username: string
  fullName: string
}
