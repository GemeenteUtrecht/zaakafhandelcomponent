import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { TaskContextData } from '../../models/task-context';
import { UserSearch } from '../../models/user-search';
import { ReadWriteDocument, Task, User } from '@gu/models';


export interface SendMessageForm {
  processInstanceId: string;
  message: string;
}

@Injectable({
  providedIn: 'root'
})
export class KetenProcessenService {

  constructor(private http: ApplicationHttpClient) { }

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
    return this.isTaskAssigned(task) && user.username === task.assignee.username
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
    if (task.assignee === null || task.assignee.username === null) {
      return true;
    }

    return this.isTaskAssignedToUser(user, task);
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

  getProcesses(mainZaakUrl: string): Observable<any> {
    const endpoint = encodeURI(`/api/camunda/fetch-process-instances?zaak_url=${mainZaakUrl}`);
    return this.http.Get(endpoint);
  }

  getFormLayout(taskId: string): Observable<TaskContextData> {
    const endpoint = encodeURI(`/api/camunda/task-data/${taskId}`);
    return this.http.Get<TaskContextData>(endpoint);
  }

  sendMessage(formData: SendMessageForm): Observable<SendMessageForm> {
    const endpoint = encodeURI("/api/camunda/send-message");
    return this.http.Post<SendMessageForm>(endpoint, formData);
  }

  getAccounts(searchInput: string): Observable<UserSearch>{
    const endpoint = encodeURI(`/api/accounts/users?search=${searchInput}`);
    return this.http.Get<UserSearch>(endpoint);
  }

  getCurrentUser(): Observable<User> {
    const endpoint = encodeURI("/api/accounts/users/me");
    return this.http.Get<User>(endpoint);
  }

  putTaskData(taskId: string, formData) {
    const endpoint = encodeURI(`/api/camunda/task-data/${taskId}`);
    return this.http.Put(endpoint, formData);
  }

  readDocument(endpoint) {
    return this.http.Post<ReadWriteDocument>(endpoint);
  }

}
