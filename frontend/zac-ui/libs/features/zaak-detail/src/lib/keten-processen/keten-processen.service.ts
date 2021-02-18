import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { TaskContextData } from '../../models/task-context';
import { UserSearch } from '../../models/user-search';

export interface SendMessageForm {
  processInstanceId: string;
  message: string;
}

@Injectable({
  providedIn: 'root'
})
export class KetenProcessenService {

  constructor(private http: ApplicationHttpClient) { }

  getProcesses(mainZaakUrl: string): Observable<any> {
    const endpoint = encodeURI(`/api/camunda/fetch-process-instances?zaak_url=${mainZaakUrl}`);
    return this.http.Get(endpoint);
  }

  getFormLayout(taskId: string): Observable<TaskContextData> {
    const endpoint = encodeURI(`/api/camunda/task-data/${taskId}`);
    return this.http.Get(endpoint);
  }

  sendMessage(formData: SendMessageForm): Observable<any> {
    const endpoint = encodeURI("/api/camunda/send-message");
    return this.http.Post(endpoint, formData);
  }

  getAccounts(searchInput: string): Observable<UserSearch>{
    const endpoint = encodeURI(`/accounts/api/users?search=${searchInput}`);
    return this.http.Get<UserSearch>(endpoint);
  }

  putTaskData(taskId: string, formData) {
    const endpoint = encodeURI(`/api/camunda/task-data/${taskId}`);
    return this.http.Put(endpoint, formData);
  }
}
