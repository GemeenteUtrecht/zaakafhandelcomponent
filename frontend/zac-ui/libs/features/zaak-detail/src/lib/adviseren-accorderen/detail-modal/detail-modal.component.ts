import { Component, Input, OnChanges } from '@angular/core';
import { Observable } from 'rxjs';
import { ApplicationHttpClient } from '@gu/services';
import { Review, ReviewDetail } from './detail-modal.interface';
import { RowData, Table } from '@gu/models';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'gu-detail-modal',
  templateUrl: './detail-modal.component.html',
  styleUrls: ['./detail-modal.component.scss']
})
export class DetailModalComponent implements OnChanges {
  @Input() uuid: string;

  data: Review[];
  title: string;
  readonly ACCORDERINGEN = "Accorderingen";
  readonly ADVIEZEN = "Adviezen";

  tableData: Table = {
    headData: [],
    bodyData: []
  }
  tableHeadApproval = ['Akkoord', 'Van', 'Gegeven op', 'Toelichting'];
  tableHeadAdvice = ['Advies', 'Van', 'Gegeven op', 'Documentadviezen'];

  isLoading: boolean;

  pipe = new DatePipe("nl-NL");

  constructor(private http: ApplicationHttpClient) { }

  ngOnChanges(): void {
    if(this.uuid) {
      this.fetchReviewDetails()
    }
  }

  fetchReviewDetails() {
    this.isLoading = true;
    this.getReviewRequestDetail(this.uuid).subscribe(res => {
      switch (res.reviewType) {
        case 'approval':
          this.formatTableDataApproval(res);
          this.title = this.ACCORDERINGEN;
          break;
        case 'advice':
          this.formatTableDataAdvice(res);
          this.title = this.ADVIEZEN;
          break;
      }
      this.data = res.reviews;
      this.isLoading = false;
    }, errorRes => {

    })
  }

  formatTableDataAdvice(data): void {
    this.tableData.headData = this.tableHeadAdvice;
    this.tableData.bodyData = data.reviews.map( (review: Review) => {
      const author = review.author['firstName']
        ? `${review.author['firstName']} ${review.author['lastName']}`
        : review.author['username'];
      const date = this.pipe.transform(review.created, 'short');
      const docAdviezen = review.documents ? review.documents.length.toString() : '-';

      const cellData: RowData = {
        cellData: {
          advies: review.advice,
          van: author,
          datum: date,
          docAdviezen: docAdviezen
        }
      }
      return cellData;
    })
  }

  formatTableDataApproval(data): void {
    this.tableData.headData = this.tableHeadApproval;
    this.tableData.bodyData = data.reviews.map( (review: Review) => {
      const icon = review.status === 'Akkoord' ? 'done' : 'close'
      const iconColor = review.status === 'Akkoord' ? 'green' : 'red'
      const author = review.author['firstName']
        ? `${review.author['firstName']} ${review.author['lastName']}`
        : review.author['username'];
      const date = this.pipe.transform(review.created, 'short');

      const cellData: RowData = {
        cellData: {
          akkoord: {
            type: 'icon',
            label: icon,
            iconColor: iconColor
          },
          van: author,
          datum: date,
          toelichting: review.toelichting
        }
      }
      return cellData;
    })
  }

  getReviewRequestDetail(uuid): Observable<ReviewDetail> {
    const endpoint = encodeURI(`/api/kownsl/zaak-review-requests/${uuid}/detail`);
    return this.http.Get<ReviewDetail>(endpoint);
  }
}
