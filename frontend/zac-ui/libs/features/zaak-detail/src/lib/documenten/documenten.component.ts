import { Component, OnInit } from '@angular/core';
import { CellData, Table, RowData } from '@gu/models';
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
  tableData: Table = {
    headData: ['Op slot', 'Type', 'Bestandsnaam', 'Vertrouwelijkheid', 'Bestandsgrootte'],
    tableData: []
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
    this.getDocuments().subscribe( data => {
      this.tableData.tableData = this.formatTableData(data)
      this.data = data;
      this.isLoading = false;
    }, error => {
      console.log(error);
      this.isLoading = false;
    })
  }

  getDocuments(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/core/cases/${this.bronorganisatie}/${this.identificatie}/documents`);
    return this.http.Get<ReviewRequest>(endpoint);
  }

  formatTableData(data): RowData[] {
   return data.map( element => {
     const cellData: RowData = {
       cellData: {
         opSlot: {
           type: 'icon',
           value: element.locked ? 'lock' : 'lock_open'
         },
         type: element.informatieobjecttype['omschrijving'],
         bestandsnaam: {
           type: 'link',
           value: element.bestandsnaam,
           url: element.downloadUrl
         },
         vertrouwelijkheid: element.vertrouwelijkheidaanduiding,
         bestandsgrootte: `${element.bestandsomvang} KB`
       }
     }
     return cellData;
    })
  }
}
