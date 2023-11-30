import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { AccessRequests } from '../../models/access-request';
import { Table } from '@gu/models';
import { zakenTableHead } from '../../constants/zaken-tablehead';
import { FeaturesWorkstackService } from '../../features-workstack.service';
import { SnackbarService } from '@gu/components';

@Component({
  selector: 'gu-workstack-access-requests',
  templateUrl: './workstack-access-requests.component.html',
  styleUrls: ['./workstack-access-requests.component.scss']
})
export class WorkstackAccessRequestsComponent implements OnInit {
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();
  accessRequestData: {count: number, next: string, previous: string, results: AccessRequests[]};
  isLoading: boolean;
  pageNumber = 1;
  sortValue: any;
  constructor(
    private workstackService: FeaturesWorkstackService,
    private snackbarService: SnackbarService,
  ) { }

  ngOnInit(): void {
    this.getContextData(1);
  }

  /**
   * Fetches access requests
   * @param page
   * @param sortData
   */
  getContextData(page, sortData?) {
    this.isLoading = true;
    this.workstackService.getWorkstackAccessRequests(page, sortData).subscribe(
      (res) => {
        this.accessRequestData = res;
        this.isLoading = false;
      }, this.reportError.bind(this))
  }

  /**
   * When paginator gets fired.
   * @param page
   */
  onPageSelect(page) {
    this.pageNumber = page.pageIndex + 1;
    this.getContextData(this.pageNumber, this.sortValue);
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param res
   */
  reportError(res) {
    const errorMessage = res.error?.detail
      ? res.error.detail
      : res.error?.nonFieldErrors
        ? res.error.nonFieldErrors[0]
        : 'Toegangsverzoeken ophalen mislukt';

    this.isLoading = false;
    this.snackbarService.openSnackBar(errorMessage, 'Sluiten', 'warn');
    console.error(res);
  }
}
