import { Component, OnInit } from '@angular/core';
import { FeaturesReportsService } from './features-reports.service';
import { ReportCase, ReportCases, ReportType } from './models/report';
import { FormBuilder, FormControl, FormGroup } from '@angular/forms';
import { RowData, Table } from '@gu/models';
import { tableHead } from './constants/table';

@Component({
  selector: 'gu-features-reports',
  templateUrl: './features-reports.component.html',
  styleUrls: ['./features-reports.component.scss'],
})
export class FeaturesReportsComponent implements OnInit {

  isLoading: boolean;
  reportTypes: ReportType[];
  reportCases: ReportCases;

  reportForm: FormGroup;

  reportCasesTableData: Table = new Table(tableHead, [])

  hasError: boolean;
  errorMessage: string;

  constructor(
    private reportsService: FeaturesReportsService,
    private fb: FormBuilder
  ) {
    this.reportForm = this.fb.group({
      reportType: this.fb.control(""),
    })
  }

  ngOnInit(): void {
    this.fetchReportTypes();
  }

  onReportTypeSelect() {
    this.reportCases = null;
    const selectedReport = this.reportType.value;
    if (selectedReport) {
      this.fetchReportCases(selectedReport)
    }
  }

  formatReportTable(data: ReportCase[]) {
    return data.map((element) => {
      const url = `/ui/zaken/${element.bronorganisatie}/${element.identificatie}`;
      const eigenschappen = element.eigenschappen?.map(e => `${e.eigenschap.naam}: ${e.value}`).join('\n')
      const cellData: RowData = {
        cellData: {
          zaaknummer: {
            type: 'link',
            label: element.identificatie,
            url: url
          },
          zaaktype: element.zaaktype.omschrijving,
          startdatum: element.startdatum,
          status: element.status,
          toelichting: element.toelichting
        },
        expandData: eigenschappen
      };
      return cellData;
    });
  }

  sortTable(sortValue) {
    const selectedReport = this.reportType.value;
    this.fetchReportCases(selectedReport, sortValue);
  }

  fetchReportTypes() {
    this.isLoading = true;
    this.reportsService.getReportTypes().subscribe((res) => {
      this.reportTypes = res;
      this.isLoading = false;
      this.hasError = false;
    }, res => {
      this.setError(res)
    });
  }

  fetchReportCases(reportId, sortValue?) {
    this.isLoading = true;
    this.reportsService.getReportCases(reportId, sortValue).subscribe((res) => {
      this.reportCases = res;
      this.reportCasesTableData.bodyData = this.formatReportTable(res.results);
      this.isLoading = false;
      this.hasError = false;
    }, res => {
      this.setError(res)
    });
  }

  setError(res) {
    this.hasError = true;
    this.errorMessage = res.error?.detail ? res.error.detail :
      res.error?.nonFieldErrors ? res.error.nonFieldErrors[0] : "Er is een fout opgetreden."
    this.isLoading = false;
  }

  get reportType(): FormControl {
    return this.reportForm.get('reportType') as FormControl;
  };

}
