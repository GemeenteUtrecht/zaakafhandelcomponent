import { Component, EventEmitter, OnInit, Output, ViewChild } from '@angular/core';
import { RowData, Table, WorkstackCase } from '@gu/models';
import { zakenTableHead } from '../../constants/zaken-tablehead';
import { FeaturesWorkstackService } from '../../features-workstack.service';
import { PaginatorComponent, SnackbarService } from '@gu/components';

@Component({
  selector: 'gu-workstack-cases',
  templateUrl: './workstack-cases.component.html',
  styleUrls: ['./workstack-cases.component.scss']
})
export class WorkstackCasesComponent implements OnInit {
  @ViewChild(PaginatorComponent) paginator: PaginatorComponent;
  zakenData: {count: number, next: string, previous: string, results: WorkstackCase[]};
  zakenTableData: Table = new Table(zakenTableHead, []);
  isLoading: boolean;
  pageNumber = 1;
  sortValue: any;

  @Output() zakenDataOutput: EventEmitter<any> = new EventEmitter<any>();

  constructor(
    private workstackService: FeaturesWorkstackService,
    private snackbarService: SnackbarService,
  ) { }

  ngOnInit(): void {
    this.getContextData(1);
  }

  /**
   * Fetches the case data
   * @param page
   * @param sortData
   */
  getContextData(page, sortData?) {
    this.isLoading = true;
    this.workstackService.getWorkstackCases(page, sortData).subscribe(
      (res) => {
        this.zakenData = res;
        this.zakenDataOutput.emit(res);
        this.zakenTableData = new Table(zakenTableHead, this.getZakenTableRows(this.zakenData.results));
        this.isLoading = false;
      }, this.reportError.bind(this))
  }

  /**
   * Returns the table rows.
   * @param {Zaak[]} zaken
   * @return {RowData}
   */
  getZakenTableRows(zaken: WorkstackCase[]): RowData[] {
    return zaken.map((element) => {
      const zaakUrl = `/ui/zaken/${element.bronorganisatie}/${element.identificatie}/acties`;

      const cellData: RowData = {
        cellData: {
          identificatie: {
            type: 'link',
            label: element.identificatie,
            url: zaakUrl,
          },
          omschrijving: element.omschrijving,
          zaaktype: element.zaaktype.omschrijving,
          zaakstatus: element.status?.statustype || '',
          startdatum: {
            type: element.startdatum ? 'date' : 'text',
            date: element.startdatum
          },
          einddatum: {
            type: element.deadline ? 'date' : 'text',
            date: element.deadline
          },
          trust: element.vertrouwelijkheidaanduiding
        },
      };
      return cellData;
    });
  }

  /**
   * Sorts the zaken (cases).
   * @param {{value: string, order: string}} sortValue
   */
  sortZaken(sortValue): void {
    this.paginator.firstPage();
    this.pageNumber = 1;
    this.sortValue = sortValue;
    this.getContextData(this.pageNumber, this.sortValue);
  }

  /**
   * When paginator gets fired.
   * @param page
   */
  onPageSelect(page) {
    this.pageNumber = page.pageIndex + 1;
    this.getContextData(this.pageNumber, this.sortValue);
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param res
   */
  reportError(res) {
    const errorMessage = res.error?.detail
      ? res.error.detail
      : res.error?.nonFieldErrors
        ? res.error.nonFieldErrors[0]
        : 'Zaken in behandling ophalen mislukt';

    this.isLoading = false;
    this.snackbarService.openSnackBar(errorMessage, 'Sluiten', 'warn');
    console.error(res);
  }
}
