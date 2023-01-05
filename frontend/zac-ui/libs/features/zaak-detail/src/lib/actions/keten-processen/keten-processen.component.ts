import {
  Component,
  Input,
  Output,
  OnChanges,
  AfterViewInit,
  EventEmitter,
  OnDestroy,
  ViewEncapsulation, SimpleChanges
} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {ModalService, SnackbarService} from '@gu/components';
import {TaskContextData} from '../../../models/task-context';
import {KetenProcessenService, SendMessageForm} from './keten-processen.service';
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
  @Output() updateCase = new EventEmitter<Zaak>();
  @Output() nTaskDataEvent = new EventEmitter<number>();

  data: KetenProcessen[];
  allTaskData: Task[];
  nVisibleTaskData: number;
  processInstanceId: string;

  debugTask: Task = null;
  newestTaskId: string;

  isExpanded = false;
  isLoading = true;
  isStartingProcess = false;
  isLoadingAction = false;
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

  showOverlay: boolean;
  showActions: boolean;

  hasCancelCaseMessage: boolean;

  constructor(
    public ketenProcessenService: KetenProcessenService,
    private zaakService: ZaakService,
    private snackbarService: SnackbarService,
    private modalService: ModalService,
    private userService: UserService,
    private route: ActivatedRoute,
  ) {
  }

  /**
   * Detect a change in the url to get the current url params.
   * Updated data will be fetched if the params change.
   */
  ngOnChanges(changes: SimpleChanges): void {
    this.route.params.subscribe(params => {
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'];

      this.checkActionsVisibility()
      this.fetchCurrentUser();

      if (JSON.stringify(changes.zaak.currentValue) !== JSON.stringify(changes.zaak.previousValue)) {
        if (!this.zaak.resultaat && !this.isPolling && !this.showOverlay) {
          this.isLoading = true;
          this.fetchProcesses();
        } else {
          this.isLoading = false;
        }
      }
    });
  }

  /**
   * A callback method that performs custom clean-up, invoked immediately before a directive, pipe, or service instance is destroyed.
   */
  ngOnDestroy(): void {
    this.cancelPolling();
  }

  /**
   * Check if a the url has the param "user-task". If so,
   * the user task should be opened in a pop-up.
   */
  ngAfterViewInit(): void {
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
    this.userService.getCurrentUser().subscribe(
      ([user,]) => this.currentUser = user,
      (error) => this.reportError(error)
    )
  }

  /**
   * Start polling
   */
  startPollingProcesses(): void {
    this.isPolling = true;
    this.fetchPollProcesses();
  }

  /**
   * Poll tasks every 5 seconds.
   */
  async fetchPollProcesses(): Promise<void> {
    let currentTaskIds;
    if (this.isPolling) {
      // Fetch processes.
      this.ketenProcessenService.getProcesses(this.mainZaakUrl).subscribe(async resData => {
        if (JSON.stringify(this.data) !== JSON.stringify(resData)) {
          currentTaskIds = this.data && this.data.length ? await this.ketenProcessenService.mergeTaskData(this.data) : null;
          // Create array of ids for comparison
          let currentTaskIdsArray = [];
          if (currentTaskIds?.length > 0) {
            currentTaskIdsArray = [...await currentTaskIds?.map(({ id }) => id)];
          }

          const newTaskIds = await this.ketenProcessenService.mergeTaskData(resData);
          const newTaskIdsArray = [...await newTaskIds?.map(({ id }) => id)];

          // Update data
          await this.updateProcessData(resData);

          // Set new task
          const newTask = await this.ketenProcessenService.findNewTask(resData, currentTaskIds);
          this.setNewestTask(newTask);

          const difference = currentTaskIdsArray
            .filter(x => !newTaskIdsArray.includes(x))
            .concat(newTaskIdsArray.filter(x => !currentTaskIdsArray.includes(x)));

          if (this.isLoadingAction && difference.length > 0) {
            if (newTask) {
              this.executeTask(newTask.id);
            }
            this.isLoadingAction = false;
          }
        }

        // Poll every 5s
        setTimeout(() => {
          this.fetchPollProcesses();
        }, this.pollingInterval)

        // Reset fail counter
        this.nPollingFails = 0;

        this.isLoading = false;
      }, () => {
        // Add to fail counter
        this.nPollingFails += 1;

        // Poll again after 5s if it fails
        setTimeout(() => {
          if (this.nPollingFails < 5) {
            this.fetchPollProcesses();
          } else {
            this.isLoading = false;
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
  cancelPolling(): void {
    if (this.isPolling) {
      this.isPolling = false;
    }
  }

  /**
   * Sets the id of the newest task.
   */
  setNewestTask(newestTask): void {
    if (newestTask) {
      this.newestTaskId = newestTask.id;
    }
  }

  /**
   * Set task that is responsible for closing the case.
   * @param {string[]} messages
   */
  setCloseCaseMessage(messages: string[]): void {
    this.hasCancelCaseMessage = messages.includes('Zaak annuleren');
  }

  /**
   * Fetch all the related processes from the zaak.
   * @param {boolean} [openTask=false] Whether to automatically execute a newly created task (task not already known).
   * @param {boolean} [waitForIt] Wait for new task to pop up.
   */
  async fetchProcesses(openTask: boolean = false, waitForIt?: boolean): Promise<void> {
    if (!this.isPolling) {
      // Known tasks after initialization.
      const currentTaskIds = openTask && this.data && this.data.length ? await this.ketenProcessenService.mergeTaskData(this.data) : null;

      // Fetch processes.
      this.ketenProcessenService.getProcesses(this.mainZaakUrl).subscribe(async data => {
        // Update data.
        await this.updateProcessData(data, !waitForIt);

        // Execute newly created task.
        if (openTask && currentTaskIds && data && data.length) {
          // Find first task if with id not in taskIds.
          const newTask = await this.ketenProcessenService.findNewTask(data, currentTaskIds);
          this.setNewestTask(newTask);
          if (newTask) {
            this.executeTask(newTask.id);
            this.isLoadingAction = false;
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
    } else {
      this.isLoading = false;
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

    this.isLoadingAction = true;
    const formData: SendMessageForm = {
      processInstanceId: this.processInstanceId,
      message: message
    }
    this.ketenProcessenService.sendMessage(formData).subscribe(result => {
      this.fetchProcesses(true, result.waitForIt);
      const sendMessageConfirmation = 'De taak wordt aangemaakt, een moment geduld.'
      this.snackbarService.openSnackBar(sendMessageConfirmation, 'Sluiten', 'primary')
    }, errorRes => {
      this.isLoading = false;
      this.isLoadingAction = false;
      this.errorMessage = errorRes?.error?.detail || 'Het openen van de actie is niet gelukt. Controleer of de actie al actief is in het "Acties" blok hierboven.';
      this.reportError(errorRes);
    })
  }

  /**
   * Updates the context data.
   * @param data
   * @param forceUpdateParent
   */
  async updateProcessData(data, forceUpdateParent = true) {
    // Update data.
    this.data = data;
    this.allTaskData = await this.ketenProcessenService.mergeTaskData(data);

    this.setCloseCaseMessage(data[0]?.messages || []);

    // Process instance ID for API calls
    this.processInstanceId = data.length > 0 ? data[0].id : null;

    this.nVisibleTaskData = this.allTaskData.length;

    // Emit number of tasks
    this.nTaskDataEvent.emit(this.allTaskData.length);

    // Trigger update in parent
    if (forceUpdateParent) {
      this.update.emit();
    }
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
    }, () => {
      this.contextErrorMessage = "Er is een fout opgetreden bij het laden van de taak."
      this.contextHasError = true;
      this.isLoadingContext = false;
    })
  }

  /**
   * Fetches the case details.
   */
  fetchCaseDetails() {
    this.zaakService.retrieveCaseDetails(this.bronorganisatie, this.identificatie)
      .subscribe( res => {
        this.zaak = res;
        setTimeout(() => {
          if (this.zaak.hasProcess === false) {
            this.fetchCaseDetails();
          } else {
            this.checkActionsVisibility();
            this.isStartingProcess = false;
            if (!this.isPolling) {
              this.startPollingProcesses();
            }
          }
        }, 2000)
      }, err => {
        this.reportError(err.error);
      })
  }

  //
  // Events.
  //

  initiateCamundaProcess() {
    this.isStartingProcess = true;
    this.zaakService.startCaseProcess(this.bronorganisatie, this.identificatie).subscribe(() => {
      setTimeout(() => {
        this.showOverlay = false;
      }, 2000)
      this.fetchCaseDetails();
    }, error => {
      this.isLoading = false;
      this.isStartingProcess = false;
      this.errorMessage = error.error?.value
        ? error.error?.value[0]
        : error?.error?.detail || error?.error.reason || error?.error[0]?.reason || error?.error.nonFieldErrors?.join(', ') || "Het opstarten van het proces is mislukt. Probeer het nog eens."
      this.reportError(error);
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
    this.isLoading = true;
    this.fetchProcesses();
  }

  /**
   * Force update of other components.
   */
  handleStartProcessSuccess(): void {
    this.isLoading = true;
    this.update.emit();
    this.showActions = true;
    this.closeModal();
  }

  /**
   * Show actions and overlay.
   */
  checkActionsVisibility() {
    this.showOverlay = !this.zaak.resultaat && !this.zaak?.isStatic && !this.zaak?.hasProcess && !this.zaak?.isConfigured;
    this.showActions = !this.zaak.resultaat && !this.zaak?.isStatic && this.zaak?.hasProcess;
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

    // Clear loading indicator to remove spinner.
    this.isLoading = false;
    this.isLoadingAction = false;
    this.isLoadingContext = false;
    this.isStartingProcess = false;
  }
}
