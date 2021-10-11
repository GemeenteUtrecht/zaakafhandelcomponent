import { Component, OnInit } from '@angular/core';
import { FeaturesDashboardService } from './features-dashboard.service';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { SnackbarService } from '@gu/components';
import { Board, Column } from './models/dashboard';
import { BoardItem } from './models/board-item';
import { Zaak } from '@gu/models';
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
  errorMessage: string;

  dashboardForm: FormGroup

  boards: Board[];
  columns: Column[];
  boardItems: BoardItem[];

  openAddItem: boolean;

  constructor(
    private dashboardService: FeaturesDashboardService,
    private snackbarService: SnackbarService,
    private fb: FormBuilder,
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

  get selectedBoardControl(): FormControl {
    return this.dashboardForm.get('selectedBoard') as FormControl;
  };

  get selectedCaseControl(): FormControl {
    return this.dashboardForm.get('selectedCase') as FormControl;
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
   * Retrieve all available boards.
   */
  getContextData(): void {
    this.isLoading = true;
    this.dashboardService.listBoards().subscribe(res => {
      this.boards = res;
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
      if (paramBoardSlug && this.boards.some(b => b.slug === paramBoardSlug)) {
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
      this.getBoardItems(selectedBoard);
      this.columns = this.boards.find(board => board.slug === selectedBoard).columns
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
   * Retrieves all board items.
   * @param {string} slug
   */
  getBoardItems(slug: string): void {
    this.isLoading = true;
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
