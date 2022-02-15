import {Component, Input, OnInit} from '@angular/core';
import {TaskHistoryService} from './task-history.service';
import {Table, Zaak} from '@gu/models';
import {SnackbarService} from '@gu/components';
import {HistoricalUserTaskData, HistoricalUserTaskDataItem} from './historical-user-task-data';

@Component({
  selector: 'gu-task-history',
  templateUrl: './task-history.component.html',
})
export class TaskHistoryComponent implements OnInit {
  @Input() mainZaakUrl: string;

  /** @type {boolean} Whether the API is loading. */
  isLoading = false;

  /** @type {Table} The tables to render. */
  table: Table = null;

  readonly errorMessage = 'Er is een fout opgetreden bij het laden van de taak geschiedenis.'

  /**
   * Constructor method.
   * @param {SnackbarService} snackbarService
   * @param {TaskHistoryService} taskHistoryService
   */
  constructor(private snackbarService: SnackbarService, private taskHistoryService: TaskHistoryService) {
  }


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
   * Retrieves the data/context.
   */
  getContextData(): void {
    this.isLoading = true;
    this.taskHistoryService.retrieveHistoricalUserTaskDataOfZaak(this.mainZaakUrl).subscribe({
      next: (historicalUserTasksData: HistoricalUserTaskData[]) => this.table = this.getTable(historicalUserTasksData),
      error: this.reportError.bind(this),
      complete: () => this.isLoading = false,
    })
  }

  /**
   * Returns the table to render.
   * @param {HistoricalUserTaskData} historicalUserTasksData
   */
  getTable(historicalUserTasksData: HistoricalUserTaskData[]): Table {
    return {
      headData: ['Name', 'Assignee', 'Created', 'Completed'],
      bodyData: historicalUserTasksData.map((historicalUserTaskData: HistoricalUserTaskData) => ({
          cellData: {
            name: historicalUserTaskData.name,
            assignee: historicalUserTaskData.assignee.fullName || historicalUserTaskData.assignee.username,
            created: {date: historicalUserTaskData.created, type: 'date'},
            completed: {date: historicalUserTaskData.completed, type: 'date'},
          },
          nestedTableData: {
            headData: ['Label', 'Naam', 'Waarde'],
            bodyData: historicalUserTaskData.history.map((historicalUserTaskDataItem: HistoricalUserTaskDataItem) => ({
              cellData: {
                label: historicalUserTaskDataItem.label,
                naam: historicalUserTaskDataItem.naam,
                waarde: {
                  label: historicalUserTaskDataItem.waarde,
                  target: '_blank',
                  type: (historicalUserTaskDataItem.waarde.match('http')) ? 'link' : 'text',
                  url: historicalUserTaskDataItem.waarde,
                },
              }
            }))
          }
        }))
    }
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    const message = error.error.value[0] || this.errorMessage;
    this.snackbarService.openSnackBar(message, 'Sluiten', 'warn');
    console.error(error);

    this.isLoading = false;
  }
}
