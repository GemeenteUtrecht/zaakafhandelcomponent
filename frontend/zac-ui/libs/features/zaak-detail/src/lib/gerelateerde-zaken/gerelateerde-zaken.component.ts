import { Component, Input, OnInit } from '@angular/core';
import { Table } from '@gu/models';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { ReviewRequest } from '../../../../kownsl/src/models/review-request';
import { ModalService } from '@gu/components';

@Component({
  selector: 'gu-gerelateerde-zaken',
  templateUrl: './gerelateerde-zaken.component.html',
  styleUrls: ['./gerelateerde-zaken.component.scss']
})
export class GerelateerdeZakenComponent implements OnInit {
  @Input() mainZaakUrl: string;

  tableData: Table = {
    headData: ['Status', 'Zaak ID', 'Resultaat', 'Aard'],
    bodyData: []
  }

  data: any;
  isLoading = true;
  bronorganisatie: string;
  identificatie: string;

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
    this.fetchRelatedCases();
  }

  fetchRelatedCases() {
    this.isLoading = true;
    this.getRelatedCases().subscribe( data => {
      this.tableData.bodyData = this.formatTableData(data);
      this.data = data;
      this.isLoading = false;
    }, error => {
      console.log(error);
      this.isLoading = false;
    })
  }

  getRelatedCases(): Observable<ReviewRequest> {
    const endpoint = encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}/related-cases`);
    return this.http.Get<ReviewRequest>(endpoint);
  }

  formatTableData(data){
    return data.map( element => {
      return {
        cellData: {
          status: element.zaak.status ? element.zaak.status.statustype.omschrijving : '-',
          zaakId: {
            type: 'link',
            label: element.zaak.identificatie,
            url: `/core/zaken/${element.zaak.bronorganisatie}/${element.zaak.identificatie}`
          },
          resultaat: element.zaak.resultaat ? element.zaak.resultaat : '-',
          aard: element.aardRelatie ? element.aardRelatie : '-',
        }
      }
    })
  }

  openModal(id: string) {
    this.modalService.open(id);
  }
}
