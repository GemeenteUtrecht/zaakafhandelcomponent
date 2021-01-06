import { Component, OnInit } from '@angular/core';
import { Table } from '@gu/models';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { ReviewRequest } from '../../../../kownsl/src/models/review-request';

@Component({
  selector: 'gu-documenten',
  templateUrl: './documenten.component.html',
  styleUrls: ['./documenten.component.scss']
})
export class DocumentenComponent implements OnInit {
  // tableData: Table = {
  //   headData: ['Type', 'Bestandsnaam', 'Vertrouwelijkheid', 'Aanmaakdatum'],
  //   elementData: [
  //     {
  //       cellData: {
  //         status: "bijlage",
  //         zaakId: "Bouwtekening.pdf",
  //         behandelaar: "Openbaar",
  //         resultaat: "23 maart 2020",
  //       }
  //     },
  //     {
  //       cellData: {
  //         status: "bijlage",
  //         zaakId: "Bouwtekening.pdf",
  //         behandelaar: "Openbaar",
  //         resultaat: "23 maart 2020",
  //       }
  //     },
  //   ]
  // }
  tableData: Table = {
    headData: ['Type', 'Bestandsnaam', 'Vertrouwelijkheid', 'Aanmaakdatum'],
    elementData: []
  }

  data: any;
  isLoading = true;
  bronorganisatie: string;
  identificatie: string;

  constructor(
    private http: ApplicationHttpClient,
    private route: ActivatedRoute
  ) {
    this.route.paramMap.subscribe( params => {
      this.bronorganisatie = params.get('bronorganisatie');
      this.identificatie = params.get('identificatie');
    });
  }

  ngOnInit(): void {
    this.isLoading = true;
    this.getRelatedCases().subscribe( data => {
      console.log(data);
      this.formatTableData(data)
      this.isLoading = false;
    }, error => {
      console.log(error);
      this.isLoading = false;
    })
  }

  getRelatedCases(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/core/cases/${this.bronorganisatie}/${this.identificatie}/documents`);
    return this.http.Get<ReviewRequest>(endpoint);
  }

  formatTableData(data){
    console.log(data);
    this.tableData.elementData = data.map( element => {
      console.log(element.zaak.url);
      return {
        cellData: {
          type: element.zaak.status.statustype.omschrijving,
          zaakId: {
            title: element.zaak.identificatie,
            link: `/core/zaken/${element.zaak.bronorganisatie}/${element.zaak.identificatie}`
          },
          resultaat: element.zaak.resultaat,
          aard: element.aardRelatie,
        }
      }
    })
  }
}
