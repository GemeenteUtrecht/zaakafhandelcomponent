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

  getReportCases(id, sortData): Observable<ReportCases> {
    const sortOrder = sortData?.order === 'desc' ? '-' : '';
    const sortValue = sortData ? tableHeadMapping[sortData.value] : '';
    console.log(tableHeadMapping);
    console.log(sortValue);
    const sortParameter = sortData ? `?ordering=${sortOrder}${sortValue}` : '';
    const endpoint = encodeURI(`/api/search/reports/${id}/results/${sortParameter}`);
    return this.http.Get<ReportCases>(endpoint);
  }

}
