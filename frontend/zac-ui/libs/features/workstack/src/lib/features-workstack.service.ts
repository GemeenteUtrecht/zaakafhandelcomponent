import {Injectable} from '@angular/core';
import {forkJoin, Observable, of} from 'rxjs';
import {catchError} from 'rxjs/operators';
import {ApplicationHttpClient} from '@gu/services';
import {Tab} from './constants/tabs';
import { ListDocuments, WorkstackSummary } from '@gu/models';

@Injectable({
  providedIn: 'root',
})
export class FeaturesWorkstackService {
  constructor(private http: ApplicationHttpClient) {}

  /**
   * Receive summary of all workstack tabs.
   * @returns {Observable<WorkstackSummary>}
   */
  getWorkstackSummary(): Observable<WorkstackSummary> {
    const endpoint = '/api/workstack/summary';
    return this.http.Post<WorkstackSummary>(endpoint);
  }

  getData(endpoint, page, sortData?) {
    const pageValue = page ? `?page=${page}` : '';
    const sortOrder = sortData?.order === 'desc' ? '-' : '';
    const sortValue = sortData ? sortData.value?.toLowerCase() : '';
    const sortParameter = sortData ? `&ordering=${sortOrder}${sortValue}` : '';
    const url = encodeURI(`${endpoint}${pageValue}${sortParameter}&pageSize=20`);
    return this.http.Get<any>(url);
  }

  /**
   * Get sorted work stack cases.
   * @param page
   * @param sortData
   * @returns {Observable<any>}
   */
  getWorkstackCases(page, sortData?): Observable<any> {
    const endpoint = '/api/workstack/cases';
    return this.getData(endpoint, page, sortData);
  }

  /**
   * Get workstack tasks
   * @param endpoint
   * @param page
   * @param sortData
   * @returns {Observable<any>}
   */
  getWorkstackTasks(endpoint, page, sortData?): Observable<any> {
    return this.getData(endpoint, page, sortData);
  }

  /**
   * Get sorted work stack reviews.
   * @param page
   * @param sortData
   * @returns {Observable<any>}
   */
  getWorkstackReviews(page, sortData?): Observable<any> {
    const endpoint = '/api/workstack/review-requests';
    return this.getData(endpoint, page, sortData);
  }

  /**
   * Get activities
   * @param endpoint
   * @param page
   * @param sortData
   * @returns {Observable<any>}
   */
  getWorkstackActivities(endpoint, page, sortData?): Observable<any> {
    return this.getData(endpoint, page, sortData);
  }

  /**
   * Get checklists
   * @param endpoint
   * @param page
   * @param sortData
   * @returns {Observable<any>}
   */
  getWorkstackChecklists(endpoint, page, sortData?): Observable<any> {
    return this.getData(endpoint, page, sortData);
  }

  /**
   * Get workstack access requests.
   * @param page
   * @param sortData
   * @returns {Observable<any>}
   */
  getWorkstackAccessRequests(page, sortData?): Observable<any> {
    const endpoint = '/api/workstack/access-requests';
    return this.getData(endpoint, page, sortData);
  }

}
