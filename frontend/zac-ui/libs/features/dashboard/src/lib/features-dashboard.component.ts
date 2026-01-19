import { Component, OnInit } from '@angular/core';
import { FeaturesDashboardService } from './features-dashboard.service';
import { UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import { SnackbarService } from '@gu/components';
import { BoardItem, Dashboard, DashboardColumn, Zaak } from '@gu/models';
import { ActivatedRoute, Router } from '@angular/router';


/**
 * Dashboard functionality to keep progress
 * of the status of a zaak.
 */
@Component({
  selector: 'gu-features-dashboard',
  templateUrl: './features-dashboard.component.html',
  styleUrls: ['./features-dashboard.component.scss']
})
export class FeaturesDashboardComponent implements OnInit {

  isLoading: boolean;
  isPolling: boolean;
  nPollingFails: number;
  errorMessage: string;

  dashboardForm: UntypedFormGroup

  dashboards: Dashboard[];
  columns: DashboardColumn[];
  boardItems: BoardItem[];

  openAddItem: boolean;

  constructor(
    private dashboardService: FeaturesDashboardService,
    private snackbarService: SnackbarService,
    private fb: UntypedFormBuilder,
    private activatedRoute: ActivatedRoute,
    private router: Router
  ) {
    this.dashboardForm = this.fb.group({
      selectedBoard: this.fb.control(""),
      selectedCase: this.fb.control("", Validators.required),
    })
  }

  //
  // Getters / setters.
  //

  get selectedBoardControl(): UntypedFormControl {
    return this.dashboardForm.get('selectedBoard') as UntypedFormControl;
  };

  get selectedCaseControl(): UntypedFormControl {
    return this.dashboardForm.get('selectedCase') as UntypedFormControl;
  };

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.getContextData();
  }

  //
  // Context.
  //

  /**
   * Retrieve all available dashboards.
   */
  getContextData(): void {
    this.isLoading = true;
    this.dashboardService.listBoards().subscribe(res => {
      this.dashboards = res;
      this.openQueryParamBoard()
      this.isLoading = false;
    }, (error) => {
        this.reportError(error);
        this.isLoading = false;
    })
  }

  /**
   * Open board according to query param.
   */
  openQueryParamBoard(): void {
    this.activatedRoute.queryParams.subscribe(queryParams => {
      const paramBoardSlug = queryParams['board']
      if (paramBoardSlug && this.dashboards.some(b => b.slug === paramBoardSlug)) {
        this.selectedBoardControl.patchValue(paramBoardSlug);
        this.onBoardSelect();
      }
    });
  }

  /**
   * Retrieves board items according to selected board.
   */
  onBoardSelect(): void {
    this.columns = null;
    const selectedBoard = this.selectedBoardControl.value;
    if (selectedBoard) {
      this.isLoading = true;
      this.isPolling = true;
      this.pollBoardItems();
      this.getBoardItems(selectedBoard);
      this.columns = this.dashboards.find(board => board.slug === selectedBoard).columns
    }
    this.activatedRoute.queryParams.subscribe(() => {
      this.router.navigate([], {
        relativeTo: this.activatedRoute,
        queryParams: {
          board: selectedBoard
        },
        skipLocationChange: true
      });
    });
  }

  /**
   * Retrieves dashboard items every 5s
   */
  pollBoardItems(): void {
    const selectedBoardSlug = this.selectedBoardControl.value;
    if (selectedBoardSlug && this.isPolling) {
      this.dashboardService.getBoardItems(selectedBoardSlug).subscribe( res => {
        this.boardItems = res;
        this.isLoading = false;

        // Poll every 5s
        setTimeout(() => {
          this.pollBoardItems();
        }, 5000)

        // Reset fail counter
        this.nPollingFails = 0;
      }, (error) => {
        this.reportError(error);
        this.isLoading = false;

        // Add to fail counter
        this.nPollingFails += 1;

        // Poll again after 5s if it fails
        setTimeout(errorRes => {
          this.errorMessage = errorRes.error.detail || 'Dashboards ophalen mislukt. Ververs de pagina om het nog eens te proberen.';
          this.reportError(errorRes);

          if (this.nPollingFails < 5) {
            this.pollBoardItems();
          } else {
            this.isPolling = false;
            this.nPollingFails = 0;
          }
        }, 5000)
      })
    }
  }

  /**
   * Retrieves all board items.
   * @param {string} slug
   */
  getBoardItems(slug: string): void {
    this.dashboardService.getBoardItems(slug).subscribe( res => {
      this.boardItems = res;
      this.isLoading = false;
    }, (error) => {
      this.reportError(error);
      this.isLoading = false;
    })
  }

  /**
   * Returns zaak url.
   * @param zaak
   * @returns {string}
   */
  createRouteLink(zaak): string {
    return `/zaken/${zaak.bronorganisatie}/${zaak.identificatie}`
  }

  /**
   * Sets selected case in form.
   * @param {Zaak} zaak
   */
  selectCase(zaak: Zaak) {
    this.selectedCaseControl.patchValue(zaak.url);
  }

  /**
   * Calls API to create a board item.
   */
  createBoardItem() {
    this.isLoading = true;
    const zaakUrl = this.selectedCaseControl.value;
    const formData = {
      objectType: "zaak",
      object: zaakUrl,
      columnUuid: this.columns[0].uuid
    }
    this.dashboardService.createBoardItem(formData)
      .subscribe( () => {
        this.getBoardItems(this.selectedBoardControl.value);
        this.isLoading = true;
        this.openAddItem = false;
        this.selectedCaseControl.reset();
      }, error => {
        this.reportError(error);
        this.isLoading = false;
      })
  }

  /**
   * Moves item to left column
   * @param {BoardItem} boardItem
   * @param {number} columnIndex
   */
  moveItemToLeftColumn(boardItem: BoardItem, columnIndex: number): void {
    const newColumnUuid = this.columns[columnIndex - 1].uuid;
    this.moveItemToColumn(boardItem, newColumnUuid)
  }

  /**
   * Moves item to right column.
   * @param {BoardItem} boardItem
   * @param {number} columnIndex
   */
  moveItemToRightColumn(boardItem: BoardItem, columnIndex: number): void {
    const newColumnUuid = this.columns[columnIndex + 1].uuid;
    this.moveItemToColumn(boardItem, newColumnUuid)
  }


  /**
   * Move item to given column.
   * @param {BoardItem} boardItem
   * @param {string} newColumnUuid
   */
  moveItemToColumn(boardItem: BoardItem, newColumnUuid: string): void {
    const formData = {
      object: boardItem.zaak.url,
      columnUuid: newColumnUuid
    }
    this.dashboardService.updateBoardItem(boardItem.uuid, formData)
      .subscribe( () => {
        this.getBoardItems(this.selectedBoardControl.value);
      }, error => {
        this.reportError(error);
        this.isLoading = false;
      })
  }

  /**
   * Deletes board item.
   * @param {BoardItem} boardItem
   */
  deleteItem(boardItem: BoardItem): void {
    this.dashboardService.deleteBoardItem(boardItem.uuid)
      .subscribe( () => {
        this.getBoardItems(this.selectedBoardControl.value);
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
