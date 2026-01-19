import {Component, Input, OnChanges} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {ModalService, SnackbarService} from '@gu/components';
import { RelatedCase, Table, Zaak } from '@gu/models';
import {ZaakService} from '@gu/services';

@Component({
  selector: 'gu-gerelateerde-zaken',
  templateUrl: './gerelateerde-zaken.component.html',
  styleUrls: ['./gerelateerde-zaken.component.scss']
})
export class GerelateerdeZakenComponent implements OnChanges {
  @Input() zaak: Zaak

  readonly errorMessage = 'Er is een fout opgetreden bij het ophalen van gerelateerde zaken.';

  tableData: Table = new Table(['Zaaknummer', 'Zaaktype', 'Omschrijving', 'Aard relatie', ''], []);

  data: any;
  isLoading = true;

  constructor(
    private route: ActivatedRoute,
    private snackbarService: SnackbarService,
    private modalService: ModalService,
    private zaakService: ZaakService,
  ) {
  }

  ngOnChanges(): void {
    this.fetchRelatedCases();
  }

  //
  // Context
  //

  /**
   * Retrieve all related cases
   */
  fetchRelatedCases() {
    this.isLoading = true;
    this.zaakService.listRelatedCases(this.zaak.bronorganisatie, this.zaak.identificatie).subscribe(data => {
      this.tableData.bodyData = this.formatTableData(data);
      this.data = data;
      this.isLoading = false;
    }, this.reportError.bind(this))
  }

  /**
   * Creates table layout for related cases
   * @param data
   * @returns {any}
   */
  formatTableData(data) {
    return data.map((element: RelatedCase) => {
      const eigenschappenArray = [
        `Resultaat: ${element.zaak.resultaat ? element.zaak.resultaat : '-'}`,
        `Status: ${element.zaak.status ? element.zaak.status.statustype.omschrijving : '-'}`,
      ]
      const eigenschappen = eigenschappenArray.join('\n')
      return {
        cellData: {
          zaaknummer: {
            type: 'link',
            label: element.zaak.identificatie,
            url: `/ui/zaken/${element.zaak.bronorganisatie}/${element.zaak.identificatie}`
          },
          zaaktype: element.zaak.zaaktype.omschrijving ? element.zaak.zaaktype.omschrijving : '-',
          omschrijving: element.zaak.omschrijving,
          aardRelatie: element.aardRelatie,
          verwijderen: {
            type: 'button',
            label: 'Verwijderen',
            value: element.zaak.url,
          },
        },
        expandData: eigenschappen
      }
    })
  }

  //
  // Events
  //

  /**
   * Removes a related case on button click
   * @param event
   */
  onTableButton(event) {
    if (event.verwijderen) {
      const formData = {
        bijdragezaak: event.verwijderen,
        hoofdzaak: this.zaak.url
      }
      this.zaakService.deleteRelatedCase(formData).subscribe(() => {
        this.fetchRelatedCases();
      }, error => {
        this.reportError(error);
      })
    }
  }

  /**
   * Opens modal
   * @param {string} id
   */
  openModal(id: string) {
    this.modalService.open(id);
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}
