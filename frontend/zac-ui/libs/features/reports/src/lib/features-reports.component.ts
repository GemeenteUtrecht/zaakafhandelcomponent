import { Component, OnInit } from '@angular/core';
import { FeaturesReportsService } from './features-reports.service';
import { ReportCase, ReportCases, ReportType } from './models/report';
import { UntypedFormBuilder, UntypedFormControl, UntypedFormGroup } from '@angular/forms';
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

  reportForm: UntypedFormGroup;

  reportCasesTableData: Table = new Table(tableHead, [])

  hasError: boolean;
  errorMessage: string;

  page = 1;
  resultLength = 0;

  constructor(
    private reportsService: FeaturesReportsService,
    private fb: UntypedFormBuilder,
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
      this.fetchReportCases(selectedReport, this.page)
    }
  }

  formatReportTable(data: ReportCase[]) {
    return data.map((element) => {
      const url = `/ui/zaken/${element.bronorganisatie}/${element.identificatie}`;
      const eigenschappen = element.eigenschappen?.map(e => `${e.eigenschap.naam}: ${e.waarde}`).join('\n')
      const cellData: RowData = {
        cellData: {
          zaaknummer: {
            type: 'link',
            label: element.identificatie,
            url: url
          },
          zaaktype: element.zaaktype.omschrijving,
          startdatum: {
            type: element.startdatum ? 'date' : 'text',
            date: element.startdatum
          },
          status: element.status.statustype,
          toelichting: element.status.statustoelichting
        },
        expandData: eigenschappen
      };
      return cellData;
    });
  }

  sortTable(sortValue) {
    const selectedReport = this.reportType.value;
    this.fetchReportCases(selectedReport, this.page, sortValue);
  }

  onPageSelect(page) {
    this.page = page.pageIndex + 1;
    const selectedReport = this.reportType.value;
    this.fetchReportCases(selectedReport, this.page)
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

  fetchReportCases(reportId, page?, sortValue?) {
    this.isLoading = true;
    this.reportsService.getReportCases(reportId, page, sortValue).subscribe((res) => {
      this.reportCases = res;
      this.resultLength = res.count;
      this.reportCasesTableData = new Table(tableHead, this.formatReportTable(res.results));
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

  get reportType(): UntypedFormControl {
    return this.reportForm.get('reportType') as UntypedFormControl;
  };

}
