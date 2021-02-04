import { Component, Input, OnChanges } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { ApplicationHttpClient } from '@gu/services';
import { ReviewDetail } from './detail-modal.interface';
import { RowData } from '@gu/models';

@Component({
  selector: 'gu-detail-modal',
  templateUrl: './detail-modal.component.html',
  styleUrls: ['./detail-modal.component.scss']
})
export class DetailModalComponent implements OnChanges {
  @Input() uuid: string;

  isLoading: boolean;
  reviewType: 'approval' | 'advice';

  constructor(private http: ApplicationHttpClient) { }

  ngOnChanges(): void {
    if(this.uuid) {
      this.fetchReviewDetails()
    }
  }

  fetchReviewDetails() {
    this.isLoading = true;
    this.getReviewRequestDetail(this.uuid).subscribe(res => {
      this.reviewType = res.reviewType;
    }, errorRes => {

    })
  }

  formatTableData(data): RowData[] {
    return data.map( element => {
      const icon = element.completed === 'Akkoord' ? 'done' : 'close'
      const iconColor = element.completed === 'Akkoord' ? 'green' : 'red'
      const reviewType =
        element.reviewType === 'approval' ? 'Akkoord'
          : element.reviewType === 'advice' ? 'Advies'
          : ''
      const completed = `${element.completed}/${element.numAssignedUsers}`

      const cellData: RowData = {
        cellData: {
          akkoord: {
            type: 'icon',
            label: icon,
            iconColor: iconColor
          },
          type: reviewType,
          completed: completed
        },
        clickOutput: element.id
      }
      return cellData;
    })
  }

  getReviewRequestDetail(uuid): Observable<ReviewDetail> {
    const endpoint = encodeURI(`/api/kownsl/zaak-review-requests/${uuid}/detail`);
    return this.http.Get<ReviewDetail>(endpoint);
  }
}
