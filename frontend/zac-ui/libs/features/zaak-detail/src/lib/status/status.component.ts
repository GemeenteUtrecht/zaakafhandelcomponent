import { Component, Input, OnInit } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { ApplicationHttpClient } from '@gu/services';

@Component({
  selector: 'gu-status',
  templateUrl: './status.component.html',
  styleUrls: ['./status.component.scss']
})
export class StatusComponent implements OnInit {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() progress: number;
  @Input() deadline: string;
  @Input() finished: boolean;

  data: any;
  isLoading: boolean;

  isExpanded = false;

  constructor(
    private http: ApplicationHttpClient,
  ) { }

  /**
   * Updates the component using a public interface.
   */
  public update() {
    this.getContextData();
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.isLoading = true;

    this.getContextData().subscribe(data => {
      this.data = data;
      this.isLoading = false;
    }, error => {
      console.log(error);
      this.isLoading = false;
    })
  }

  //
  // Context.
  //

  /**
   * Fetches the statuses.
   */
  getContextData(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}/statuses`);
    return this.http.Get<any>(endpoint);
  }
}
