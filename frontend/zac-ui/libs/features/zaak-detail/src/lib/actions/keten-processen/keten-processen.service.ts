import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { TaskContextData } from '../../../models/task-context';
import { Messages, ReadWriteDocument, Task, User, UserSearch } from '@gu/models';
import { UserGroupList } from '../../../models/user-group-search';


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
   * Returns wether a task is for the current user.
   * @param {User} user
   * @param {Task} task
   * @returns {boolean}
   */
  isTaskForCurrentUser(user: User, task: Task): boolean {
    return (task.assignee?.username === user.username || user.groups.includes(task.assignee?.name));
  }

  /**
   * Returns wether a task is for other users.
   * @param {User} user
   * @param {Task} task
   * @returns {boolean}
   */
  isTaskForOtherUser(user: User, task: Task): boolean {
    return (task.assignee?.username !== user.username && !user.groups.includes(task.assignee?.name));
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
    return this.isTaskAssigned(task) && (user.username === task.assignee.username || user.groups.includes(task.assignee.name));
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
    } else {
      return true;
    }
  }

  /**
   * Returns a new task if present.
   * @param newTaskIds
   * @param currentTaskIds
   * @returns {Task}
   */
  async findNewTask(newTaskIds, currentTaskIds): Promise<Task> {
    if (JSON.stringify(currentTaskIds) !== JSON.stringify(newTaskIds)) {
      return newTaskIds.filter(item => !currentTaskIds.some(itemToBeRemoved => itemToBeRemoved.id === item.id))[0]
    }
    return;
  }

  /**
   * Retrieve processes.
   * @param {string} mainZaakUrl
   * @returns {Observable<any>}
   */
  getTasks(mainZaakUrl: string): Observable<any> {
    const endpoint = encodeURI(`/api/camunda/fetch-tasks?zaakUrl=${mainZaakUrl}`);
    return this.http.Get(endpoint);
  }

  /**
   * Receive messages to create a new task.
   * @param {string} mainZaakUrl
   * @returns {Observable<Messages[]>}
   */
  getMessages(mainZaakUrl: string): Observable<Messages[]> {
    const endpoint = encodeURI(`/api/camunda/fetch-messages?zaakUrl=${mainZaakUrl}`);
    return this.http.Get(endpoint);
  }

  /**
   * Retrieve layout of the task.
   * @param {string} taskId
   * @returns {Observable<TaskContextData>}
   */
  getFormLayout(taskId: string): Observable<TaskContextData> {
    const endpoint = encodeURI(`/api/camunda/task-data/${taskId}`);
    return this.http.Get<TaskContextData>(endpoint);
  }

  /**
   * Sends message to create a new task.
   * @param {SendMessageForm} formData
   * @returns {Observable<*>}
   */
  sendMessage(formData: SendMessageForm): Observable<any> {
    const endpoint = encodeURI("/api/camunda/send-message");
    return this.http.Post<SendMessageForm>(endpoint, formData);
  }

  /**
   * Retrieve all accounts.
   * @param {string} searchInput
   * @returns {Observable<UserSearch>}
   */
  getAccounts(searchInput: string): Observable<UserSearch>{
    const endpoint = encodeURI(`/api/accounts/users?search=${searchInput}`);
    return this.http.Get<UserSearch>(endpoint);
  }

  /**
   * Retrieve all user groups.
   * @param {string} searchInput
   * @returns {Observable<UserGroupList>}
   */
  getUserGroups(searchInput: string): Observable<UserGroupList>{
    const endpoint = encodeURI(`/api/accounts/groups?search=${searchInput}`);
    return this.http.Get<UserGroupList>(endpoint);
  }

  /**
   * Assign task to user or group.
   * @param formData
   * @returns {Observable<any>}
   */
  postAssignTask(formData) {
    const endpoint = encodeURI('/api/camunda/claim-task');
    return this.http.Post<any>(endpoint, formData)
  }

  /**
   * Update task data.
   * @param {string} taskId
   * @param formData
   * @returns {Observable<unknown>}
   */
  putTaskData(taskId: string, formData) {
    const endpoint = encodeURI(`/api/camunda/task-data/${taskId}`);
    return this.http.Put(endpoint, formData);
  }

  /**
   * Cancel task.
   * @param formData
   */
  cancelTask(formData) {
    const endpoint = encodeURI('/api/camunda/cancel-task');
    return this.http.Post(endpoint, formData);
  }

  /**
   * Open document.
   * @param endpoint
   * @returns {Observable<ReadWriteDocument>}
   */
  readDocument(endpoint) {
    return this.http.Post<ReadWriteDocument>(endpoint);
  }

  /**
   * Compare arrays by id
   * @param arr1
   * @param arr2
   * @returns {{areEqual: boolean} | {areEqual: boolean}}
   */
  compareArraysById(arr1, arr2) {
    // Check if the arrays have the same length
    if (arr1?.length !== arr2?.length) {
      return { areEqual: false };
    }

    // Create sets of the ids from each array
    const idSet1 = new Set(arr1.map(obj => obj.id));
    const idSet2 = new Set(arr2.map(obj => obj.id));

    // Check if the sets of ids are equal
    if (idSet1.size !== idSet2.size || !this.isSetEqual(idSet1, idSet2)) {
      return { areEqual: false };
    }

    // All ids are equal, arrays are considered equal
    return { areEqual: true };
  }

  /**
   * Check if sets are equal
   * @param set1
   * @param set2
   * @returns {boolean}
   */
  isSetEqual(set1, set2) {
    for (const item of set1) {
      if (!set2.has(item)) {
        return false;
      }
    }

    return true;
  }
}
