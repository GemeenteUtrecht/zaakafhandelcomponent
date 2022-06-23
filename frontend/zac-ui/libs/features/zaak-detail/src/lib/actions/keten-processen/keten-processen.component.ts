import {
  Component,
  Input,
  Output,
  OnChanges,
  AfterViewInit,
  EventEmitter,
  OnDestroy,
  ViewEncapsulation
} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {ModalService, SnackbarService} from '@gu/components';
import {TaskContextData} from '../../../models/task-context';
import {KetenProcessenService} from './keten-processen.service';
import {KetenProcessen} from '../../../models/keten-processen';
import {Task, User, Zaak} from '@gu/models';
import {UserService, ZaakService} from '@gu/services';


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
  styleUrls: [
    './keten-processen.component.scss',
  ],
  encapsulation: ViewEncapsulation.None,

})

export class KetenProcessenComponent implements OnChanges, OnDestroy, AfterViewInit {
  @Input() mainZaakUrl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() currentUser: User;
  @Input() zaak: Zaak;

  @Output() update = new EventEmitter<any>();
  @Output() nTaskDataEvent = new EventEmitter<number>();

  data: KetenProcessen[];
  allTaskData: Task[];
  processInstanceId: string;

  debugTask: Task = null;
  newestTaskId: string;

  isExpanded = false;
  isLoading = true;
  isPolling = false;
  nPollingFails = 0;
  pollingInterval = 5000;

  errorMessage: string;

  // Task context data
  taskContextData: TaskContextData;
  isLoadingContext: boolean;
  contextHasError: boolean;
  contextErrorMessage: string;
  isStatic: boolean;
  hasProcess: boolean;

  // Tabs
  selectedTabIndex = null;

  // Links
  doRedirectTarget: '_blank' | '_self';

  constructor(
    public ketenProcessenService: KetenProcessenService,
    private zaakService: ZaakService,
    private snackbarService: SnackbarService,
    private modalService: ModalService,
    private userService: UserService,
    private route: ActivatedRoute,
  ) {
  }

  //
  // Getters / setters.
  //

  get showOverlay() {
    return !this.isStatic && !this.hasProcess;
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

      if (!this.zaak.resultaat && !this.isPolling) {
        this.fetchProcesses();
      }
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
      if (userTaskId && !this.zaak.resultaat) {
        this.executeTask(userTaskId);
      }
    });
  }

  /**
   * Fetches the current user.
   */
  fetchCurrentUser(): void {
    this.userService.getCurrentUser().subscribe(([user,]) => {
      this.currentUser = user;
    })
  }

  /**
   * Poll tasks every 5 seconds.
   */
  startPollingProcesses() {
    this.isPolling = true;
    this.fetchPollProcesses();
  }

  fetchPollProcesses() {
    if (this.isPolling) {
      this.ketenProcessenService.getProcesses(this.mainZaakUrl).subscribe(resData => {
        if (resData[0].title === "Zaak Aanmaken") {
          this.updateProcessData(resData);
          if (this.allTaskData?.length === 0) {
            this.isPolling = false;
            this.isStatic = false;
            this.hasProcess = false;
            console.log('has process');
          }
        }
        if (JSON.stringify(this.data) !== JSON.stringify(resData)) {
          const currentTaskIds = this.data && this.data.length ? this.ketenProcessenService.mergeTaskData(this.data) : null;
          this.setNewestTask(resData, currentTaskIds);
          this.updateProcessData(resData);
        }

        // Poll every 5s
        setTimeout(() => {
          this.fetchPollProcesses();
        }, this.pollingInterval)

        // Reset fail counter
        this.nPollingFails = 0;
      }, () => {
        // Add to fail counter
        this.nPollingFails += 1;

        // Poll again after 5s if it fails
        setTimeout(errorRes => {
          if (this.nPollingFails < 5) {
            this.fetchPollProcesses();
          } else {
            this.isPolling = false;
            this.nPollingFails = 0;
          }
        }, this.pollingInterval)
      });
    }
  }

  /**
   * Cancels the polling of tasks.
   */
  cancelPolling() {
    if (this.isPolling) {
      this.isPolling = false;
    }
  }

  /**
   * Sets the id of the newest task.
   */
  setNewestTask(data, taskIds) {
    const newestTask = this.ketenProcessenService.findNewTask(data, taskIds);
    if (newestTask) {
      this.newestTaskId = newestTask.id;
    }
  }

  /**
   * Fetch all the related processes from the zaak.
   * @param {boolean} [openTask=false] Whether to automatically execute a newly created task (task not already known).
   */
  fetchProcesses(openTask: boolean = false): void {
    if (!this.isPolling) {
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
          const newTask = this.ketenProcessenService.findNewTask(data, currentTaskIds);
          this.setNewestTask(data, currentTaskIds)

          if (newTask) {
            this.executeTask(newTask.id);
          }
        }

        this.isLoading = false;

        // Start polling
        setTimeout(() => {
          this.startPollingProcesses();
        }, this.pollingInterval)
      }, errorRes => {
        this.isLoading = false;
        this.errorMessage = errorRes?.error?.detail || 'Taken ophalen mislukt. Ververs de pagina om het nog eens te proberen.';
        this.reportError(errorRes);
      })
    }
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
      const sendMessageConfirmation = 'De taak wordt aangemaakt, een moment geduld.'
      this.snackbarService.openSnackBar(sendMessageConfirmation, 'Sluiten', 'primary')
    }, errorRes => {
      this.isLoading = false;
      this.errorMessage = errorRes?.error?.detail || 'Het openen van de taak is niet gelukt. Probeer het nog eens.';
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

    // Process instance ID for API calls
    this.processInstanceId = data.length > 0 ? data[0].id : null;

    // Trigger update in parent
    this.update.emit(data);

    // Emit number of tasks
    this.nTaskDataEvent.emit(this.allTaskData.length);
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

  //
  // Events.
  //

  initiateCamundaProcess() {
    this.isLoading = true;
    this.zaakService.startCaseProcess(this.bronorganisatie, this.identificatie).subscribe(() => {
      this.isLoading = false;
    }, err => {
      this.isLoading = false;
      this.errorMessage = "Het opstarten van het proces is mislukt. Probeer het nog eens."
      this.reportError(err);
    })
  }

  /**
   * Gets called when a task date label is double clicked.
   * @param task
   */
  taskDblClick(task) {
    if (this.debugTask) {
      this.debugTask = null;
      return;
    }
    this.debugTask = task;
  }

  /**
   * Opens a modal.
   * @param {string} id The id of the modal to open.
   */
  openModal(id: string): void {
    this.modalService.open(id);
  }

  /**
   * Closes modal and reloads services.
   */
  closeModal(): void {
    this.modalService.close('ketenprocessenModal');
    this.fetchProcesses();
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
