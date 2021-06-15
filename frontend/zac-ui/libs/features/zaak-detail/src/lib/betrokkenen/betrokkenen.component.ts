import { Component, Input, OnChanges } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';

@Component({
  selector: 'gu-betrokkenen',
  templateUrl: './betrokkenen.component.html',
  styleUrls: ['./betrokkenen.component.scss']
})
export class BetrokkenenComponent implements OnChanges {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  hiddenRoleData: any;
  alwaysVisibleRoleData: any;
  allRoleData: any;
  isLoading = true;
  isExpanded: boolean;

  constructor(private http: ApplicationHttpClient) { }

  ngOnChanges(): void {
    this.isLoading = true;
    this.getRoles().subscribe(data => {
      this.allRoleData = data;
      this.hiddenRoleData = data.slice(0, -3);
      this.alwaysVisibleRoleData = data.slice(-3)
      this.isLoading = false;
    }, error => {
      console.error(error);
      this.isLoading = false;
    })
  }

  getRoles(): Observable<any> {
    const endpoint = encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}/roles`);
    return this.http.Get<any>(endpoint);
  }

  formatRoles(data) {
    this.alwaysVisibleRoleData = data.slice(-3)
  }
}
