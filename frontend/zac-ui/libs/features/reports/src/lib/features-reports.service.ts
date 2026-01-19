import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { ReportType, ReportCases } from './models/report';
import { tableHeadMapping } from './constants/table';

@Injectable({
  providedIn: 'root',
})
export class FeaturesReportsService {
  constructor(private http: ApplicationHttpClient) {}

  getReportTypes(): Observable<ReportType[]> {
    const endpoint = '/api/search/reports';
    return this.http.Get<ReportType[]>(endpoint);
  }

  getReportCases(id, page, sortData): Observable<ReportCases> {
    const pageValue = `?page=${page}`;
    const sortOrder = sortData?.order === 'desc' ? '-' : '';
    const sortValue = sortData ? tableHeadMapping[sortData.value] : '';
    const sortParameter = sortData ? `&ordering=${sortOrder}${sortValue}` : '';
    const endpoint = encodeURI(`/api/search/reports/${id}/results/${pageValue}${sortParameter}`);
    return this.http.Get<ReportCases>(endpoint);
  }

}
