import {
  Component,
  Input,
  Output,
  OnChanges,
  AfterViewInit,
  EventEmitter,
  OnDestroy,
  ViewEncapsulation, SimpleChanges, HostListener
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import {ModalService, SnackbarService} from '@gu/components';
import {TaskContextData} from '../../../models/task-context';
import {KetenProcessenService, SendMessageForm} from './keten-processen.service';
import { Task, User, Zaak } from '@gu/models';
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

  allTaskData: Task[];
  nVisibleTaskData: number;
  processInstanceId: string;
  messages: string[];

  debugTask: Task = null;
  newestTaskId: string;

  isExpanded = false;
  isLoading = true;
  isStartingProcess = false;
  isLoadingAction = false;
  isPolling = false;
  nPolls = 0;
  nPollingFails = 0;
  pollingInterval = 2000;

  errorMessage: string;

  // Task context data
  taskContextData: TaskContextData;
  isLoadingContext: boolean;
  contextHasError: boolean;
  contextErrorMessage: string;
  timeoutId: number;

  maxUserInactivityTime = 30 * 1000; // 30 seconds
  isUserInactive = false;

  // Tabs
  selectedTabIndex = null;

  // Links
  doRedirectTarget: '_blank' | '_self';

  showOverlay: boolean;
  showTasks: boolean;
  showActions: boolean;

  hasCancelCaseMessage: boolean;

  componentIsVisible = false;

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
      if (params['tabId'] === 'acties') {
        this.componentIsVisible = true;
      }
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'];

      this.checkActionsVisibility()
      this.fetchCurrentUser();

      if (JSON.stringify(changes.zaak.currentValue) !== JSON.stringify(changes.zaak.previousValue)) {
        if (!this.isPolling && !this.showOverlay) {
          this.isLoading = true;
          this.fetchProcesses();
          this.fetchMessages();
        } else {
          this.isLoading = false;
        }
      }
    });

    this.checkTimeOut();
  }

  /**
   * A callback method that performs custom clean-up, invoked immediately before a directive, pipe, or service instance is destroyed.
   */
  ngOnDestroy(): void {
    this.cancelPolling();
  }

  /**
   * Check if the url has the param "user-task". If so,
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
    this.pollingInterval = 2000;
    this.fetchPollProcesses();
  }

  /**
   * Poll tasks every 5 seconds.
   */
  async fetchPollProcesses(): Promise<void> {
    let currentTaskIds;
    if (this.isPolling && this.componentIsVisible) {
      // Fetch processes.
      this.ketenProcessenService.getTasks(this.mainZaakUrl).subscribe(async resData => {

        const comparisonResult = this.ketenProcessenService.compareArraysById(this.allTaskData, resData);

        if (!comparisonResult.areEqual) {
          currentTaskIds = this.allTaskData && this.allTaskData.length ? this.allTaskData : null;
          // Create array of ids for comparison
          let currentTaskIdsArray = [];
          if (currentTaskIds?.length > 0) {
            currentTaskIdsArray = [...await currentTaskIds?.map(({ id }) => id)];
          }

          const newTaskIds = resData;
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

        // Set poll interval
        this.setPollInterval();

        // Reset fail counter
        this.nPollingFails = 0;

        this.isLoading = false;
        this.isLoadingAction = false;
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
   * Set polling interval.
   */
  setPollInterval() {
    this.nPolls += 1;
    if (this.nPolls >= 5 && this.pollingInterval < 5000) {
      this.pollingInterval += 1000;
      this.nPolls = 0;
    }
  }

  /**
   * Cancels the polling of tasks.
   */
  cancelPolling(): void {
    if (this.isPolling) {
      this.isPolling = false;
      this.nPolls = 0;
      this.pollingInterval = 2000;
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

  fetchMessages() {
    this.ketenProcessenService.getMessages(this.mainZaakUrl)
      .subscribe(res => {
        if (res.length > 0) {
          this.messages = res[0].messages;
          this.setCloseCaseMessage(this.messages);
          // Process instance ID for API calls
          this.processInstanceId = res[0].id;
        }
      })
  }

  /**
   * Fetch all the related processes from the zaak.
   * @param {boolean} [openTask=false] Whether to automatically execute a newly created task (task not already known).
   * @param {boolean} [waitForIt] Wait for new task to pop up.
   */
  async fetchProcesses(openTask: boolean = false, waitForIt?: boolean): Promise<void> {
    if (!this.isPolling) {
      // Known tasks after initialization.
      const currentTaskIds = openTask && this.allTaskData && this.allTaskData.length ? this.allTaskData : null;

      // Fetch processes.
      this.ketenProcessenService.getTasks(this.mainZaakUrl).subscribe(async data => {
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
      this.errorMessage = errorRes?.error?.detail || errorRes?.error?.message || 'Het openen van de actie is niet gelukt. Controleer of de actie al actief is in het "Acties" blok hierboven.';
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
    this.allTaskData = data.sort((a, b) => new Date(b.created).getTime() - new Date(a.created).getTime());

    this.nVisibleTaskData = this.allTaskData.length;

    // Emit number of tasks
    if (!this.zaak.resultaat) {
      this.nTaskDataEvent.emit(this.nVisibleTaskData);
    }

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
              this.fetchProcesses();
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

  /**
   * Clear time out if user shows activity.
   */
  @HostListener('document:mousemove')
  @HostListener('document:keypress')
  @HostListener('document:keydown')
  @HostListener('document:click')
  @HostListener('document:wheel')
  resetTimeout() {
    clearTimeout(this.timeoutId);
    if (this.isUserInactive) {
      this.startPollingProcesses();
      this.isUserInactive = false;
    }
    this.checkTimeOut();
  }

  /**
   * Log user out after timeout.
   */
  checkTimeOut() {
    // @ts-ignore
    this.timeoutId = setTimeout(() => {
      this.cancelPolling();
      this.isUserInactive = true;
    }, this.maxUserInactivityTime);
  }

  initiateCamundaProcess() {
    this.isStartingProcess = true;
    this.zaakService.startCaseProcess(this.bronorganisatie, this.identificatie).subscribe(() => {
      this.fetchCaseDetails();
    }, error => {
      this.isLoading = false;
      this.errorMessage = error.error?.value
        ? error.error?.value[0]
        : error?.error?.detail || error?.error.reason || error?.error[0]?.reason || error?.error.nonFieldErrors?.join(', ') || "Het opstarten van het proces is mislukt. Probeer het nog eens."
      this.reportError(error);
    })
  }

  /**
   * Gets called when a task date label is double-clicked.
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
    this.fetchProcesses();
    this.closeModal();
  }

  /**
   * Show actions and overlay.
   */
  checkActionsVisibility() {
    this.showTasks = !this.zaak.resultaat || (this.zaak.resultaat && this.zaak.kanGeforceerdBijwerken);

    const caseIsUnstartedAndUnconfigured = !this.zaak.resultaat && !this.zaak?.isStatic && !this.zaak?.hasProcess && !this.zaak?.isConfigured;
    const caseIsClosedAndHasForceStartPermission = this.zaak.resultaat && !this.zaak?.isStatic && !this.zaak?.hasProcess && this.zaak?.isConfigured && this.zaak.kanGeforceerdBijwerken;
    this.showOverlay = caseIsUnstartedAndUnconfigured || caseIsClosedAndHasForceStartPermission

    const caseIsActiveAndHasProcess = !this.zaak.resultaat && !this.zaak?.isStatic && this.zaak?.hasProcess && this.zaak?.isConfigured;
    const caseIsClosedAndHasProcess = this.zaak.resultaat && !this.zaak?.isStatic && this.zaak?.hasProcess;
    this.showActions = caseIsActiveAndHasProcess || caseIsClosedAndHasProcess;
  }

  /**
   * Checks if this component is visible
   * @param isVisible
   */
  public setIsVisible(isVisible){
    this.componentIsVisible = isVisible;
    if (this.componentIsVisible) {
      this.startPollingProcesses();
    } else {
      this.cancelPolling();
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
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);

    // Clear loading indicator to remove spinner.
    this.isLoading = false;
    this.isLoadingAction = false;
    this.isLoadingContext = false;
    this.isStartingProcess = false;
  }
}
