import { Component, Input, OnChanges, AfterViewInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { DatePipe } from '@angular/common';
import { ModalService } from '@gu/components'
import { TaskContextData } from '../../models/task-context';
import { KetenProcessenService } from './keten-processen.service';
import { KetenProcessen } from '../../models/keten-processen';
import { Task, User } from '@gu/models';

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

  data: KetenProcessen[];
  processInstanceId: string;

  isLoading = true;
  hasError: boolean;
  errorMessage: string;

  pipe = new DatePipe("nl-NL");

  // Send Message
  sendMessageErrorMessage: string;
  sendMessageHasError: boolean;

  // Task context data
  taskContextData: TaskContextData;
  isLoadingContext: boolean;
  contextHasError: boolean;
  contextErrorMessage: string;

  doRedirectTarget: '_blank' | '_self';

  constructor(
    private route: ActivatedRoute,
    private modalService: ModalService,
    private ketenProcessenService: KetenProcessenService,
  ) { }

  /**
   * Detect a change in the url to get the current url params.
   * Updated data will be fetched if the params change.
   */
  ngOnChanges(): void {
    this.route.params.subscribe( params => {
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
   * Returns whether task is assigned.
   * @param {Task} task
   * @return {boolean}
   */
  isTaskAssigned(task: Task): boolean {
    return Boolean(task.assignee)
  }

  /**
   * Returns whether task is assigned to user.
   * @param {User} user
   * @param {Task} task
   * @return {boolean}
   */
  isTaskAssignedToUser(user: User, task: Task): boolean {
    return user.username === task.assignee.username
  }

  /**
   * Returns whether user can perform any actions on task.
   * @param {User} user
   * @param {Task} task
   * @return {boolean}
   */
  isTaskActionableByUser(user: User, task: Task): boolean {
    return this.isUserAllowToExecuteTask(user, task) || this.isUserAllowToAssignTask(user, task)
  }

  /**
   * Returns whether user is allowed to execute task.
   * @param {Task} task
   * @param {User} user
   * @return {boolean}
   */
  isUserAllowToExecuteTask(user: User, task: Task): boolean {
    try {
      if (task.assignee.username === null) {
        return true;
      }

      return this.isTaskAssignedToUser(user, task);
    } catch(e) {
      return false;
    }
  }

  /**
   * Returns whether user is allowed to assign task.
   * @param {User} user
   * @param {Task} task
   * @return {boolean}
   */
  isUserAllowToAssignTask(user: User, task: Task): boolean {
    return user.username && !task.assignee
  }

  /**
   * Fetches the current user.
   */
  fetchCurrentUser(): void {
    this.ketenProcessenService.getCurrentUser().subscribe( res => {
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
    this.ketenProcessenService.getProcesses(this.mainZaakUrl).subscribe( data => {
      // Update data.
      this.data = data;
      this.processInstanceId = data.length > 0 ? data[0].id : null;
      this.isLoading = false;

      // Execute newly created task.
      if(openTask && taskIds && data && data.length) {
        // Find first task if with id not in taskIds.
        const newTask = data[0].tasks
            .sort((a: Task, b: Task) => new Date(b.created).getTime() - new Date(a.created).getTime())  // Newest task first.
            .find((task: Task) => taskIds.indexOf(task.id) === -1);

        if (newTask) {
          this.executeTask(newTask.id);
        }
      }
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
    this.ketenProcessenService.sendMessage(formData).subscribe( (result) => {
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
   */
  executeTask(taskId: string): void {
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
}
