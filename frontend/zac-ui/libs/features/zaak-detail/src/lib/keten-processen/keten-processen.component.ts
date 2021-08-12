import {Component, Input, Output, OnChanges, AfterViewInit, EventEmitter} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {ModalService} from '@gu/components'
import {TaskContextData} from '../../models/task-context';
import {KetenProcessenService} from './keten-processen.service';
import {KetenProcessen} from '../../models/keten-processen';
import {Task, User} from '@gu/models';

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

export class KetenProcessenComponent implements OnChanges, AfterViewInit {
  @Input() mainZaakUrl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() currentUser: User;

  @Output() update = new EventEmitter<any>();

  data: KetenProcessen[];
  allTaskData: Task[];
  processInstanceId: string;

  isExpanded = false;
  isLoading = true;
  hasError: boolean;
  errorMessage: string;

  // Send Message
  sendMessageErrorMessage: string;
  sendMessageHasError: boolean;

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
   * Fetch all the related processes from the zaak.
   * @param {boolean} [openTask=false] Whether to automatically execute a newly created task (task not already known).
   */
  fetchProcesses(openTask: boolean = false): void {
    // Known tasks after initialization.
    const taskIds = openTask && this.data && this.data.length ? this.data[0].tasks.map(task => task.id) : null;

    this.isLoading = true;
    this.hasError = false;
    this.errorMessage = '';
    this.hasError = true;

    // Fetch processes.
    this.ketenProcessenService.getProcesses(this.mainZaakUrl).subscribe(data => {
      // Update data.
      this.data = data;
      this.allTaskData = this.ketenProcessenService.mergeTaskData(data);
      this.processInstanceId = data.length > 0 ? data[0].id : null;
      this.isLoading = false;

      // Execute newly created task.
      if (openTask && taskIds && data && data.length) {
        // Find first task if with id not in taskIds.
        const newTask = data[0].tasks
          .sort((a: Task, b: Task) => new Date(b.created).getTime() - new Date(a.created).getTime())  // Newest task first.
          .find((task: Task) => taskIds.indexOf(task.id) === -1);

        if (newTask) {
          this.executeTask(newTask.id);
        }
      }

      this.update.emit(data);
    }, errorRes => {
      this.errorMessage = errorRes.error.detail;
      this.hasError = true;
      this.isLoading = false;
    })
  }

  /**
   * Send a message to Camunda.
   * The message lets Camunda know which process to start.
   * @param {string} message
   */
  sendMessage(message: string): void {
    this.isLoading = true
    const formData = {
      processInstanceId: this.processInstanceId,
      message: message
    }
    this.ketenProcessenService.sendMessage(formData).subscribe((result) => {
      this.fetchProcesses(true);
    }, errorRes => {
      this.sendMessageErrorMessage = errorRes.error.detail || 'Er is een fout opgetreden.';
      this.sendMessageHasError = true;
      this.isLoading = false;
    })
  }

  /**
   * Open a selected task.
   * @param {string} taskId
   * @param {number} [tabIndex]
   */
  executeTask(taskId: string, tabIndex: number = null): void {
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
    this.fetchProcesses()
  }
}
