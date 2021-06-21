import { Component, Input, OnChanges, AfterViewInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { DatePipe } from '@angular/common';
import { ModalService } from '@gu/components'
import { TaskContextData } from '../../models/task-context';
import { KetenProcessenService } from './keten-processen.service';
import { KetenProcessen, Task } from '../../models/keten-processen';
import { User } from '@gu/models';

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

  // Assign task
  assignTaskTask: Task;

  constructor(
    private route: ActivatedRoute,
    private modalService: ModalService,
    private ketenProcessenService: KetenProcessenService,
  ) { }

  ngOnChanges(): void {
    this.route.params.subscribe( params => {
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'];

      this.fetchCurrentUser();
      this.fetchProcesses();
    });
  }

  ngAfterViewInit() {
    this.route.queryParams.subscribe(params => {
      const userTaskId = params['user-task'];
      if (userTaskId) {
        this.executeTask(userTaskId);
      }
    });
  }

  fetchCurrentUser(): void {
    this.ketenProcessenService.getCurrentUser().subscribe( res => {
      this.currentUser = res;
    })
  }

  fetchProcesses(): void {
    this.isLoading = true;
    this.hasError = false;
    this.errorMessage = '';
    this.hasError = true;
    this.ketenProcessenService.getProcesses(this.mainZaakUrl).subscribe( data => {
      this.data = data;
      this.processInstanceId = data.length > 0 ? data[0].id : null;
      this.isLoading = false;
    }, errorRes => {
      this.errorMessage = errorRes.error.detail;
      this.hasError = true;
      this.isLoading = false;
    })
  }

  sendMessage(value): void {
    this.isLoading = true
    const formData = {
      processInstanceId: this.processInstanceId,
      message: value
    }
    this.ketenProcessenService.sendMessage(formData).subscribe( () => {
      this.fetchProcesses();
    }, errorRes => {
      this.sendMessageErrorMessage = errorRes.error.detail;
      this.sendMessageHasError = true;
      this.isLoading = false;
    })
  }

  executeTask(taskId): void {
    this.fetchFormLayout(taskId);
  }

  assignTask(task: Task) {
    this.assignTaskTask = task;
    this.modalService.open('assignTaskModal');
  }

  doRedirect(taskContext: TaskContextData) {
    if (taskContext.form === 'zac:doRedirect') {
      const target = taskContext.context.openInNewWindow ? "_blank" : "_self";
      window.open(taskContext.context.redirectTo, target);
    }
  }

  fetchFormLayout(taskId): void {
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
