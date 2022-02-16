import { Component, Input, OnInit } from '@angular/core';
import { StatusService } from './status.service';
import { SnackbarService } from '@gu/components';
import { BoardItem, Dashboard, DashboardColumn } from '@gu/models';

@Component({
  selector: 'gu-status',
  templateUrl: './status.component.html',
  styleUrls: ['./status.component.scss']
})
export class StatusComponent implements OnInit {
  @Input() mainZaakUrl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() progress: number;
  @Input() deadline: string;
  @Input() finished: boolean;

  data: any;
  dashboardColumns: DashboardColumn[];
  currentDashboard: Dashboard;
  currentDashboardItem: BoardItem;
  isLoading: boolean;
  errorMessage: string;

  isExpanded = false;

  constructor(
    private statusService: StatusService,
    private snackbarService: SnackbarService,
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
    this.getZaakStatus();
    this.getDashboardStatus()
  }

  //
  // Context.
  //

  /**
   * Get context.
   */
  getContextData(): void {
    this.getZaakStatus();
    this.getDashboardStatus()
  }

  /**
   * Fetches the case statuses.
   */
  getZaakStatus() {
    this.statusService.getZaakStatuses(this.bronorganisatie, this.identificatie).subscribe(data => {
      this.data = data;
      this.isLoading = false;
    }, error => {
      console.log(error);
      this.isLoading = false;
    })
  }

  /**
   * Fetches the dashboard statuses.
   */
  getDashboardStatus() {
    this.statusService.getDashboardStatus(this.mainZaakUrl).subscribe(data => {
      if (data[0]) {
        this.currentDashboard = data[0].board;
        this.dashboardColumns = data[0].board.columns;
        this.findCurrentDashboardItem(data);
      }
    }, error => {
      console.log(error);
    })
  }

  /**
   * Find current dashboard item.
   * @param data
   */
  findCurrentDashboardItem(data) {
    this.currentDashboardItem = data.find(item => item.zaak.url === this.mainZaakUrl);
  }

  /**
   * Triggers when user selects new dashboard status.
   * @param {DashboardColumn} column
   */
  onDashboardStatusSelect(column: DashboardColumn): void {
    const formData = {
      object: this.mainZaakUrl,
      columnUuid: column.uuid
    }
    this.statusService.updateBoardItem(this.currentDashboardItem.uuid, formData)
      .subscribe( () => {
        this.snackbarService.openSnackBar("Dashboard bijgewerkt", "Sluiten", "primary");
      }, error => {
        this.reportError(error);
        this.isLoading = false;
      })
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param res
   */
  reportError(res: any): void {
    this.errorMessage = res.error?.detail ? res.error.detail :
      res.error?.nonFieldErrors ? res.error.nonFieldErrors[0] : "Er is een fout opgetreden."
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(res);
  }
}
