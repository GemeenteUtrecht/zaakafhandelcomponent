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

  isLoading = true;
  hasError: boolean;
  errorMessage: string;

  bronorganisatie: string;
  identificatie: string;

  pipe = new DatePipe("nl-NL");

  uitvoerenType: 'advice-approve' | 'document-select' | 'dynamic-form' | 'sign-document' = "advice-approve"

  constructor(
    private http: HttpClient,
    private customHttp: ApplicationHttpClient,
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
      this.isLoading = false;
    }, res => {
      this.errorMessage = res.error.detail;
      this.hasError = true;
      this.isLoading = false;
    })
  }

  getProcesses(): Observable<any> {
    const endpoint = encodeURI(`/api/camunda/fetch-process-instances?zaak_url=${this.zaakUrl}`);
    return this.http.get(endpoint);
  }

  sendMessage(value) {
    const endpoint = encodeURI("/core/_send-message");
    const headers = new HttpHeaders().set('Content-Type', 'application/json');
    const options = {
      headers: headers,
      withCredentials: true,
    }
    this.http.post(endpoint, {"message": value}, options).subscribe( res => {
      console.log(res);
    })
  }

  executeTask(taskId) {
    console.log(taskId)
    console.log(1)
    // this.openModal()
  }

  openModal(id: string) {
    this.modalService.open(id);
  }

  closeModal(id: string) {
    this.modalService.close(id);
  }
}
