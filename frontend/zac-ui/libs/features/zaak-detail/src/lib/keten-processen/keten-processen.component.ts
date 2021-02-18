import { Component, Input, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { DatePipe } from '@angular/common';
import { ModalService } from '@gu/components'
import { TaskContextData } from '../../models/task-context';
import { KetenProcessenService } from './keten-processen.service';
import { KetenProcessen } from '../../models/keten-processen';

@Component({
  selector: 'gu-keten-processen',
  templateUrl: './keten-processen.component.html',
  styleUrls: ['./keten-processen.component.scss']
})

export class KetenProcessenComponent implements OnInit {
  @Input() mainZaakUrl: string;

  data: KetenProcessen[];
  processInstanceId: string;

  isLoading = true;
  hasError: boolean;
  errorMessage: string;

  bronorganisatie: string;
  identificatie: string;

  pipe = new DatePipe("nl-NL");

  // Send Message
  sendMessageErrorMessage: string;
  sendMessageHasError: boolean;

  // Task context data
  taskContextData: TaskContextData;
  isLoadingContext: boolean;

  constructor(
    private route: ActivatedRoute,
    private modalService: ModalService,
    private ketenProcessenService: KetenProcessenService,
  ) {
    this.route.paramMap.subscribe( params => {
      this.bronorganisatie = params.get('bronorganisatie');
      this.identificatie = params.get('identificatie');
    });
  }

  ngOnInit(): void {
    this.fetchProcesses();
  }

  fetchProcesses(): void {
    this.isLoading = true;
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

  executeTask(taskId, hasForm, executeUrl): void {
    if (!hasForm) {
      window.location = executeUrl;
    } else {
      this.fetchFormLayout(taskId);
    }
  }

  fetchFormLayout(taskId): void {
    this.isLoadingContext = true;
    this.modalService.open('custom-modal-2');
    this.ketenProcessenService.getFormLayout(taskId).subscribe(res => {
      this.taskContextData = res;
      this.isLoadingContext = false;
    })
  }

  openModal(id: string) {
    this.modalService.open(id);
  }

  closeModal(id: string) {
    this.modalService.close(id);
  }
}
