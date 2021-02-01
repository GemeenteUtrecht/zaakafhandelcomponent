import { Component, Input, OnInit } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { DatePipe } from '@angular/common';
import { ModalService } from '@gu/components'

@Component({
  selector: 'gu-keten-processen',
  templateUrl: './keten-processen.component.html',
  styleUrls: ['./keten-processen.component.scss']
})

export class KetenProcessenComponent implements OnInit {
  @Input() zaakUrl: string;

  data: any;
  processInstanceId: string;

  isLoading = true;
  hasError: boolean;
  errorMessage: string;

  bronorganisatie: string;
  identificatie: string;

  pipe = new DatePipe("nl-NL");

  sendMessageErrorMessage: string;
  sendMessageHasError: boolean;

  uitvoerenType: 'advice-approve' | 'document-select' | 'dynamic-form' | 'sign-document' = "advice-approve"

  constructor(
    private http: ApplicationHttpClient,
    private route: ActivatedRoute,
    private modalService: ModalService
  ) {
    this.route.paramMap.subscribe( params => {
      this.bronorganisatie = params.get('bronorganisatie');
      this.identificatie = params.get('identificatie');
    });
  }

  ngOnInit(): void {
    this.fetchProcesses();
  }

  fetchProcesses() {
    this.isLoading = true;
    this.getProcesses().subscribe( data => {
      this.data = data;
      this.processInstanceId = data[0].id
      this.isLoading = false;
    }, errorRes => {
      this.errorMessage = errorRes.error.detail;
      this.hasError = true;
      this.isLoading = false;
    })
  }

  getProcesses(): Observable<any> {
    const endpoint = encodeURI(`/api/camunda/fetch-process-instances?zaak_url=${this.zaakUrl}`);
    return this.http.Get(endpoint);
  }

  sendMessage(value) {
    this.isLoading = true
    const endpoint = encodeURI("/api/camunda/send-message");
    const formData = {
      processInstanceId: this.processInstanceId,
      message: value
    }
    this.http.Post(endpoint, formData).subscribe( res => {
      this.fetchProcesses();
    }, errorRes => {
      this.sendMessageErrorMessage = errorRes.error.detail;
      this.sendMessageHasError = true;
      this.isLoading = false;
    })
  }

  executeTask(taskId) {
  }

  openModal(id: string) {
    this.modalService.open(id);
  }

  closeModal(id: string) {
    this.modalService.close(id);
  }
}
