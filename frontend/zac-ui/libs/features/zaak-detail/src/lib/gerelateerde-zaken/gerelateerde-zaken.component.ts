import { Component, Input, OnInit } from '@angular/core';
import { Table } from '@gu/models';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';
import { ModalService } from '@gu/components';
import { RelatedCase } from '../../models/related-case';

@Component({
  selector: 'gu-gerelateerde-zaken',
  templateUrl: './gerelateerde-zaken.component.html',
  styleUrls: ['./gerelateerde-zaken.component.scss']
})
export class GerelateerdeZakenComponent implements OnInit {
  @Input() mainZaakUrl: string;

  tableData: Table = new Table(['Resultaat', 'Status', 'Zaak ID', 'Zaaktype', 'Aard'], []);

  data: any;
  isLoading = true;
  bronorganisatie: string;
  identificatie: string;

  constructor(
    private http: ApplicationHttpClient,
    private route: ActivatedRoute,
    private modalService: ModalService
  ) { }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'];
      this.fetchRelatedCases();
    });
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

  getRelatedCases(): Observable<RelatedCase[]> {
    const endpoint = encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}/related-cases`);
    return this.http.Get<RelatedCase[]>(endpoint);
  }

  formatTableData(data){
    return data.map( element => {
      return {
        cellData: {
          resultaat: element.zaak.resultaat ? element.zaak.resultaat : '-',
          status: element.zaak.status ? element.zaak.status.statustype.omschrijving : '-',
          zaakId: {
            type: 'link',
            label: element.zaak.identificatie,
            url: `/core/zaken/${element.zaak.bronorganisatie}/${element.zaak.identificatie}`
          },
          zaaktype: element.zaak.zaaktype.omschrijving ? element.zaak.zaaktype.omschrijving : '-',
          aard: element.aardRelatie ? element.aardRelatie : '-',
        }
      }
    })
  }

  openModal(id: string) {
    this.modalService.open(id);
  }
}
