import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { RowData, Table, Task, UserTask } from '@gu/models';
import { tasksTableHead } from '../../constants/tasks-tablehead';
import { FeaturesWorkstackService } from '../../features-workstack.service';
import { PaginatorComponent, SnackbarService } from '@gu/components';

@Component({
  selector: 'gu-workstack-tasks',
  templateUrl: './workstack-tasks.component.html',
  styleUrls: ['./workstack-tasks.component.scss']
})
export class WorkstackTasksComponent implements OnInit {
  @ViewChild(PaginatorComponent) paginator: PaginatorComponent;
  @Input() endpoint: string;
  taskData: {count: number, next: string, previous: string, results: UserTask[]};
  tasksTableData: Table = new Table(tasksTableHead, []);
  isLoading: boolean;
  pageNumber = 1;
  sortValue: any;
  @Output() taskDataOutput: EventEmitter<any> = new EventEmitter<any>();
  constructor(
    private workstackService: FeaturesWorkstackService,
    private snackbarService: SnackbarService,
  ) { }

  ngOnInit(): void {
    this.getContextData(1);
  }

  /**
   * Fetches the task data
   * @param page
   * @param sortData
   */
  getContextData(page, sortData?) {
    this.isLoading = true;
    this.workstackService.getWorkstackTasks(this.endpoint, page, sortData).subscribe(
      (res) => {
        this.taskData = res;
        this.taskDataOutput.emit(res);
        this.tasksTableData = new Table(tasksTableHead, this.getTasksTableRows(this.taskData.results));
        this.isLoading = false;
      }, this.reportError.bind(this))
  }

  /**
   * Creates table
   * @param {UserTask[]} tasks
   * @returns {RowData[]}
   */
  getTasksTableRows(tasks: UserTask[]): RowData[] {
    return tasks.map((element) => {
      const zaakUrl = `/ui/zaken/${element.zaak.bronorganisatie}/${element.zaak.identificatie}/acties`;

      const cellData: RowData = {
        cellData: {
          identificatie: {
            type: 'link',
            label: element.zaak.identificatie,
            url: zaakUrl,
          },
          task: element.task,
          omschrijving: element.zaak.omschrijving,
          zaaktype: element.zaak.zaaktype.omschrijving,
          deadline: {
            type: element.zaak.deadline ? 'date' : 'text',
            date: element.zaak.deadline
          },
        },
      };
      return cellData;
    });
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

  /**
   * Fetch sort table
   * @param sortValue
   */
  sortTable(sortValue) {
    this.paginator.firstPage();
    this.pageNumber = 1;
    this.sortValue = sortValue;
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
        : 'Taken ophalen mislukt';

    this.isLoading = false;
    this.snackbarService.openSnackBar(errorMessage, 'Sluiten', 'warn');
    console.error(res);
  }
}
