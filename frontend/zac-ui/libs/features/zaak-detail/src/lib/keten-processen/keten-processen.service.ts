import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { TaskContextData } from '../../models/task-context';
import { UserSearch } from '../../models/user-search';
import { ReadWriteDocument, Task, User } from '@gu/models';
import { KetenProcessen } from '../../models/keten-processen';
import { UserGroupSearch } from '../../models/user-group-search';


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
    return this.isTaskAssigned(task) && user.username === task.assignee.username;
  }

  /**
   * Returns whether user can perform any actions on task.
   * @param {User} user
   * @param {Task} task
   * @return {boolean}
   */
  isTaskActionableByUser(user: User, task: Task): boolean {
    return this.isUserAllowedToExecuteTask(user, task) || this.isUserAllowedToAssignTask(user, task)
  }

  /**
   * Returns whether user is allowed to execute task.
   * @param {Task} task
   * @param {User} user
   * @return {boolean}
   */
  isUserAllowedToExecuteTask(user: User, task: Task): boolean {
    if (task.assignee === null || task.assignee.username === null) {
      return true;
    }

    return this.isTaskAssignedToUser(user, task);
  }

  /**
   * Returns whether user is allowed to (re)assign a task.
   * @param {User} user
   * @param {Task} task
   * @return {boolean}
   */
  isUserAllowedToAssignTask(user: User, task: Task): boolean {
    if(['Accorderen', 'Adviseren'].indexOf(task.name) > -1) {
      return user.username && !task.assignee
    }
    return true;
  }

  /**
   * Aggregates all the tasks of the main processes and sub processes
   * @param {KetenProcessen[]} ketenProcessenData
   * @returns {Task[]}
   */
  mergeTaskData(ketenProcessenData: KetenProcessen[]): Task[] {
    if(!ketenProcessenData.length) {
      return []
    }

    const mainTasksArray = ketenProcessenData[0].tasks;
    const subTasksArray = [];
    ketenProcessenData[0].subProcesses.forEach( subProcess => {
      subProcess.tasks.forEach( task => subTasksArray.push(task))
    })

    return mainTasksArray
      .concat(subTasksArray)
      .sort((a: Task, b: Task) => new Date(b.created).getTime() - new Date(a.created).getTime());
  }

  /**
   * Returns a new task if present.
   * @param newData
   * @param currentData
   * @returns {Task}
   */
  findNewTask(newData, currentData) {
    const currentTaskIds = this.mergeTaskData(newData);
    return currentTaskIds
      .find((task: Task) => currentData.indexOf(task.id) === -1);
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

  getUserGroups(searchInput: string): Observable<UserGroupSearch>{
    const endpoint = encodeURI(`/api/accounts/groups?search=${searchInput}`);
    return this.http.Get<UserGroupSearch>(endpoint);
  }

  getCurrentUser(): Observable<User> {
    const endpoint = encodeURI("/api/accounts/users/me");
    return this.http.Get<User>(endpoint);
  }

  postAssignTask(formData) {
    const endpoint = encodeURI('/api/camunda/claim-task');
    return this.http.Post<any>(endpoint, formData)
  }

  putTaskData(taskId: string, formData) {
    const endpoint = encodeURI(`/api/camunda/task-data/${taskId}`);
    return this.http.Put(endpoint, formData);
  }

  readDocument(endpoint) {
    return this.http.Post<ReadWriteDocument>(endpoint);
  }
}
