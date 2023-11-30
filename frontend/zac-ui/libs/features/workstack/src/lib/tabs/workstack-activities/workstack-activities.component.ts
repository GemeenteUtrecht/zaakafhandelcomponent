import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { AdHocActivities, AdHocActivitiesZaak } from '../../models/activities';
import { WorkstackChecklist } from '../../models/checklist';
import { PaginatorComponent, SnackbarService } from '@gu/components';
import { FeaturesWorkstackService } from '../../features-workstack.service';
import { Table, Zaak } from '@gu/models';
import { zakenTableHead } from '../../constants/zaken-tablehead';

@Component({
  selector: 'gu-workstack-activities',
  templateUrl: './workstack-activities.component.html',
  styleUrls: ['./workstack-activities.component.scss']
})
export class WorkstackActivitiesComponent implements OnInit {
  @ViewChild(PaginatorComponent) paginator: PaginatorComponent;
  @Input() activtiesEndpoint: string;
  @Input() checklistEndpoint: string;
  activitiesData: {count: number, next: string, previous: string, results: AdHocActivities[]};
  checkListData: WorkstackChecklist[];
  isLoading: boolean;
  pageNumber = 1;
  sortValue: any;

  constructor(
    private workstackService: FeaturesWorkstackService,
    private snackbarService: SnackbarService,
  ) { }

  //
  // Getters / setters.
  //

  get nActivities(): number {
    return this.activitiesData?.count + this.checkListData?.length
  };

  ngOnInit(): void {
    this.getContextData(1);
  }

  /**
   * Fetches the activities and checklists data combined
   * @param page
   * @param sortData
   */
  getContextData(page, sortData?) {
    this.isLoading = true;
    this.workstackService.getWorkstackActivities(this.activtiesEndpoint, page, sortData).subscribe(
      (res) => {
        this.activitiesData = res
        this.isLoading = false;
      }, this.reportError.bind(this))
    this.workstackService.getWorkstackChecklists(this.checklistEndpoint, page, sortData).subscribe(
      (res) => {
        this.checkListData = res
        this.isLoading = false;
      }, this.reportError.bind(this))
  }

  /**
   * Returns the path to zaak.
   * @param {AdHocActivitiesZaak} zaak
   * @return {string}
   */
  getZaakPath(zaak: AdHocActivitiesZaak): string {
    return `/zaken/${zaak.bronorganisatie}/${zaak.identificatie}`;
  }

  //
  // Events.
  //

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
        : 'Activiteiten ophalen mislukt';

    this.isLoading = false;
    this.snackbarService.openSnackBar(errorMessage, 'Sluiten', 'warn');
    console.error(res);
  }
}
