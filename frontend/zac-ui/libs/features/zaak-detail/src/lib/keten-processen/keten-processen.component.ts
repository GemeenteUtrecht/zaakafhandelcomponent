import { Component, Input, Output, OnChanges, AfterViewInit, EventEmitter, OnDestroy } from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import { ModalService, SnackbarService } from '@gu/components';
import {TaskContextData} from '../../models/task-context';
import {KetenProcessenService} from './keten-processen.service';
import {KetenProcessen} from '../../models/keten-processen';
import {Task, User} from '@gu/models';
import { catchError, filter, finalize, switchMap, take } from 'rxjs/operators';
import { interval, of, Subscription } from 'rxjs';

import { isEqual as _isEqual } from 'lodash';

/**
 * <gu-keten-processen [mainZaakUrl]="mainZaakUrl" [bronorganisatie]="bronorganisatie" [identificatie]="identificatie"></gu-keten-processen>
 *
 * A "Ketenproces" is a process that is modelled in the Camunda BPM (Business Process Model).
 * This component allows you to start a new process or execute a process task. Process tasks
 * can also be assigned to a specific user.
 *
 * Requires mainZaakUrl: string input to identify the url of the case (zaak).
 * Requires bronorganisatie: string input to identify the organisation.
 * Requires identificatie: string input to identify the case (zaak).
 * Requires currentUsers: User input to identify the current user.
 *
 */
@Component({
  selector: 'gu-keten-processen',
  templateUrl: './keten-processen.component.html',
  styleUrls: ['./keten-processen.component.scss']
})

export class KetenProcessenComponent implements OnChanges, OnDestroy, AfterViewInit {
  @Input() mainZaakUrl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() currentUser: User;

  @Output() update = new EventEmitter<any>();

  data: KetenProcessen[];
  allTaskData: Task[];
  processInstanceId: string;

  debugTask: Task = null;
  newestTaskId: string;

  pollingSub$: Subscription;

  isExpanded = false;
  isLoading = true;
  isPolling = false;

  errorMessage: string;

  // Task context data
  taskContextData: TaskContextData;
  isLoadingContext: boolean;
  contextHasError: boolean;
  contextErrorMessage: string;

  // Tabs
  selectedTabIndex = null;

  // Links
  doRedirectTarget: '_blank' | '_self';

  constructor(
    private route: ActivatedRoute,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
    public ketenProcessenService: KetenProcessenService,
  ) {
  }

  /**
   * Detect a change in the url to get the current url params.
   * Updated data will be fetched if the params change.
   */
  ngOnChanges(): void {
    this.route.params.subscribe(params => {
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'];

      this.fetchCurrentUser();
      this.fetchProcesses();
    });
  }

  /**
   * A callback method that performs custom clean-up, invoked immediately before a directive, pipe, or service instance is destroyed.
   */
  ngOnDestroy() {
    this.cancelPolling();
  }

  /**
   * Check if a the url has the param "user-task". If so,
   * the user task should be opened in a pop-up.
   */
  ngAfterViewInit() {
    this.route.queryParams.subscribe(params => {
      const userTaskId = params['user-task'];
      if (userTaskId) {
        this.executeTask(userTaskId);
      }
    });
  }

  /**
   * Fetches the current user.
   */
  fetchCurrentUser(): void {
    this.ketenProcessenService.getCurrentUser().subscribe(res => {
      this.currentUser = res;
    })
  }

  /**
   * Poll tasks every 30 seconds.
   */
  pollProcesses() {
    const currentTaskIds = this.data && this.data.length ? this.ketenProcessenService.mergeTaskData(this.data) : null;

    this.isPolling = true;
    const pollInterval = 30000; // 30 seconds
    this.pollingSub$ = interval(pollInterval)
      .pipe(
        switchMap(x => {
          // Fetch processes
          return this.ketenProcessenService.getProcesses(this.mainZaakUrl)
            .pipe(
              catchError(errorRes => {
                this.isLoading = false;
                this.errorMessage = errorRes.error.detail || 'Taken ophalen mislukt. Ververs de pagina om het nog eens te proberen.';
                this.reportError(errorRes);
                return of(undefined);
              })
            );
        }),
        filter(data => data !== undefined)
      )
      .subscribe(resData => {
        if (!_isEqual(this.data, resData)) {
          this.setNewestTask(resData, currentTaskIds);
        }
        this.updateProcessData(resData);
      });
  }

  /**
   * Cancels the polling of tasks
   */
  cancelPolling() {
    this.isPolling = false;
    this.pollingSub$.unsubscribe();
  }

  /**
   *
   * @param newData
   * @param currentData
   * @returns {Task}
   */
  findNewTask(newData, currentData) {
    const currentTaskIds = this.ketenProcessenService.mergeTaskData(newData);
    return currentTaskIds
      .find((task: Task) => currentData.indexOf(task.id) === -1);
  }

  /**
   * Sets the id of the newest task
   */
  setNewestTask(data, taskIds) {
    const newestTask = this.findNewTask(data, taskIds);
    if (newestTask) {
      this.newestTaskId = newestTask.id;
    }
  }

  /**
   * Fetch all the related processes from the zaak.
   * @param {boolean} [openTask=false] Whether to automatically execute a newly created task (task not already known).
   */
  fetchProcesses(openTask: boolean = false): void {
    // Known tasks after initialization.
    const currentTaskIds = openTask && this.data && this.data.length ? this.ketenProcessenService.mergeTaskData(this.data) : null;

    this.isLoading = true;

    // Fetch processes.
    this.ketenProcessenService.getProcesses(this.mainZaakUrl).subscribe(data => {
      // Update data.
      this.updateProcessData(data);

      // Execute newly created task.
      if (openTask && currentTaskIds && data && data.length) {
        // Find first task if with id not in taskIds.

        const newTask = this.findNewTask(data, currentTaskIds);
        this.setNewestTask(data, currentTaskIds)

        if (newTask) {
          this.executeTask(newTask.id);
        }
      }

      this.isLoading = false;

      this.pollProcesses();
    }, errorRes => {
      this.isLoading = false;
      this.errorMessage = errorRes.error.detail || 'Er is een fout opgetreden.';
      this.reportError(errorRes);
    })
  }

  /**
   * Send a message to Camunda.
   * The message lets Camunda know which process to start.
   * @param {string} message
   */
  sendMessage(message: string): void {
    // Cancel data polling
    this.cancelPolling();

    this.isLoading = true
    const formData = {
      processInstanceId: this.processInstanceId,
      message: message
    }
    this.ketenProcessenService.sendMessage(formData).subscribe((result) => {
      this.fetchProcesses(true);
    }, errorRes => {
      this.isLoading = false;
      this.errorMessage = errorRes.error.detail || 'Er is een fout opgetreden.';
      this.reportError(errorRes);
    })
  }

  /**
   * Updates the context data.
   * @param data
   */
  updateProcessData(data) {
    // Update data.
    this.data = data;
    this.allTaskData = this.ketenProcessenService.mergeTaskData(data);
    this.processInstanceId = data.length > 0 ? data[0].id : null;

    this.update.emit(data);
  }

  /**
   * Open a selected task.
   * @param {string} taskId
   * @param {number} [tabIndex]
   */
  executeTask(taskId: string, tabIndex: number = null): void {
    this.cancelPolling() // stop polling data;

    this.selectedTabIndex = tabIndex;
    this.fetchFormLayout(taskId);
  }

  /**
   * Redirects to the given task redirect link.
   * Also checks if the link should be opened in the current window or new window.
   * @param {TaskContextData} taskContext
   */
  doRedirect(taskContext: TaskContextData) {
    if (taskContext.form === 'zac:doRedirect') {
      this.doRedirectTarget = taskContext.context.openInNewWindow ? "_blank" : "_self";
      window.open(taskContext.context.redirectTo, this.doRedirectTarget);
    }
  }

  /**
   * Fetches the data for the task.
   * @param taskId
   */
  fetchFormLayout(taskId: string): void {
    this.contextHasError = false;
    this.isLoadingContext = true;
    this.modalService.open('ketenprocessenModal');
    this.ketenProcessenService.getFormLayout(taskId).subscribe(res => {
      this.doRedirect(res)
      this.taskContextData = res;
      this.isLoadingContext = false;
    }, errorRes => {
      this.contextErrorMessage = "Er is een fout opgetreden bij het laden van de taak."
      this.contextHasError = true;
      this.isLoadingContext = false;
    })
  }

  /**
   * Closes modal and reloads services.
   */
  closeModal(): void {
    this.modalService.close('ketenprocessenModal');
    this.fetchProcesses();
  }

  //
  // Events.
  //

  /**
   * Gets called when a task date label is double clicked.
   * @param task
   */
  taskDblClick(task) {
    if(this.debugTask) {
      this.debugTask = null;
      return;
    }
    this.debugTask = task;
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}
