import { Component, OnInit } from '@angular/core';
import { CellData, Table, RowData } from '@gu/models';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { convertKbToMb } from '@gu/utils';

@Component({
  selector: 'gu-documenten',
  templateUrl: './documenten.component.html',
  styleUrls: ['./documenten.component.scss']
})
export class DocumentenComponent implements OnInit {
  tableData: Table = {
    headData: ['Op slot', 'Type', 'Bestandsnaam', 'Vertrouwelijkheid', 'Bestandsgrootte'],
    bodyData: []
  }

  data: any;

  isLoading = true;
  hasError: boolean;
  errorMessage: string;

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
      this.tableData.bodyData = this.formatTableData(data)
      this.data = data;
      this.isLoading = false;
    }, res => {
      this.errorMessage = res.error.detail;
      this.hasError = true;
      this.isLoading = false;
    })
  }

  getDocuments(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/core/cases/${this.bronorganisatie}/${this.identificatie}/documents`);
    return this.http.Get<any>(endpoint);
  }

  formatTableData(data): RowData[] {
    return data.map( element => {
     const icon = element.locked ? 'lock' : 'lock_open'
     const iconColor = element.locked ? 'green' : 'orange'
     const bestandsomvang =
       element.bestandsomvang > 999 ? `${(convertKbToMb(element.bestandsomvang, 2)).toLocaleString("nl-NL")} MB`
       : `${element.bestandsomvang} KB`

     const cellData: RowData = {
       cellData: {
         opSlot: {
           type: 'icon',
           value: icon,
           iconColor: iconColor
         },
         type: element.informatieobjecttype['omschrijving'],
         bestandsnaam: {
           type: 'link',
           value: element.bestandsnaam,
           url: element.downloadUrl
         },
         vertrouwelijkheid: element.vertrouwelijkheidaanduiding,
         bestandsomvang: bestandsomvang
       }
     }
     return cellData;
    })
  }
}
