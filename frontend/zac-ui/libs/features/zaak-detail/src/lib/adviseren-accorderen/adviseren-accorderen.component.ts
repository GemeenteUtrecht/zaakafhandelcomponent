import { Component, OnInit } from '@angular/core';
import { RowData, Table } from '@gu/models';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { ModalService } from '@gu/components';

@Component({
  selector: 'gu-adviseren-accorderen',
  templateUrl: './adviseren-accorderen.component.html',
  styleUrls: ['./adviseren-accorderen.component.scss']
})
export class AdviserenAccorderenComponent implements OnInit {
  tableData: Table = {
    headData: ['', 'Type', 'Opgehaald'],
    bodyData: []
  }

  data: any;
  isLoading = true;
  bronorganisatie: string;
  identificatie: string;

  selectedUuid: string;

  constructor(
    private http: ApplicationHttpClient,
    private route: ActivatedRoute,
    private modalService: ModalService
  ) {
    this.route.paramMap.subscribe( params => {
      this.bronorganisatie = params.get('bronorganisatie');
      this.identificatie = params.get('identificatie');
    });
  }

  ngOnInit(): void {
    this.isLoading = true;
    this.getSummary().subscribe( data => {
      this.tableData.bodyData = this.formatTableData(data)
      this.data = data;
      this.isLoading = false;
    }, error => {
      console.log(error);
      this.isLoading = false;
    })
  }

  getSummary(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/kownsl/zaak-review-requests/${this.bronorganisatie}/${this.identificatie}/summary`);
    return this.http.Get<any>(endpoint);
  }

  formatTableData(data): RowData[] {
    return data.map( element => {
      const icon = element.completed === element.numAssignedUsers ? 'assignment_turned_in' : 'timer'
      const iconColor = element.completed === element.numAssignedUsers ? 'green' : 'orange'
      const reviewType =
        element.reviewType === 'approval' ? 'Akkoord'
        : element.reviewType === 'advice' ? 'Advies'
        : ''
      const completed = `${element.completed}/${element.numAssignedUsers}`

      const cellData: RowData = {
        cellData: {
          icon: {
            type: 'icon',
            label: icon,
            iconColor: iconColor
          },
          type: reviewType,
          completed: completed
        },
        clickOutput: element.completed > 0 ? element.id : null
      }
      return cellData;
    })
  }

  handleTableClickOutput(value) {
    this.openDetailModal(value);
    this.selectedUuid = value;
    this.modalService.open('adviseren-accorderen-detail-modal')
  }

  openDetailModal(uuid) {

  }

  getReviewRequestDetail(uuid): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/kownsl/zaak-review-requests/${uuid}/detail`);
    return this.http.Get<any>(endpoint);
  }
}
