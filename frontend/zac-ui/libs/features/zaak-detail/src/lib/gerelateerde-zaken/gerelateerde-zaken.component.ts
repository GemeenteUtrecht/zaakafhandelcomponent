import { Component, Input, OnChanges } from '@angular/core';
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
export class GerelateerdeZakenComponent implements OnChanges {
  @Input() mainZaakUrl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  tableData: Table = new Table(['Zaaknummer', 'Zaaktype'], []);

  data: any;
  isLoading = true;

  constructor(
    private http: ApplicationHttpClient,
    private route: ActivatedRoute,
    private modalService: ModalService
  ) { }

  ngOnChanges(): void {
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

  getRelatedCases(): Observable<RelatedCase[]> {
    const endpoint = encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}/related-cases`);
    return this.http.Get<RelatedCase[]>(endpoint);
  }

  formatTableData(data){
    return data.map( (element: RelatedCase) => {
      const eigenschappenArray = [
        `Resultaat: ${element.zaak.resultaat ? element.zaak.resultaat : '-'}`,
        `Status: ${element.zaak.status ? element.zaak.status.statustype.omschrijving : '-'}`,
        `Aard relatie: ${element.aardRelatie ? element.aardRelatie : '-'}`
      ]
      const eigenschappen = eigenschappenArray.join('\n')
      return {
        cellData: {
          zaaknummer: {
            type: 'link',
            label: element.zaak.identificatie,
            url: `/ui/zaken/${element.zaak.bronorganisatie}/${element.zaak.identificatie}`
          },
          zaaktype: element.zaak.zaaktype.omschrijving ? element.zaak.zaaktype.omschrijving : '-'
        },
        expandData: eigenschappen
      }
    })
  }

  openModal(id: string) {
    this.modalService.open(id);
  }
}
