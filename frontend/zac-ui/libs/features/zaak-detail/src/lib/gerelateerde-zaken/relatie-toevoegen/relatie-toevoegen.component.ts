import {Component, Input, OnInit, Output, EventEmitter} from '@angular/core';
import {Choice, Field, FieldConfiguration, ModalService, SnackbarService} from '@gu/components';
import {Zaak} from '@gu/models';
import {ZaakService} from '@gu/services';

@Component({
  selector: 'gu-relatie-toevoegen',
  templateUrl: './relatie-toevoegen.component.html',
  styleUrls: ['./relatie-toevoegen.component.scss']
})
export class RelatieToevoegenComponent implements OnInit {
  @Input() mainZaakUrl: string;
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();

  form: FieldConfiguration[];
  isLoading: boolean;

  readonly errorMessage = 'Er is een fout opgetreden bij het ophalen van gerelateerde zaken.';

  readonly AARD_RELATIES: Choice[] = [
    {
      value: 'vervolg',
      label: 'Vervolg'
    },
    {
      value: 'bijdrage',
      label: 'Bijdrage'
    },
    {
      value: 'onderwerp',
      label: 'Onderwerp'
    }
  ];

  /**
   * Constructor method.
   * @param {ModalService} modalService
   * @param {SnackbarService} snackbarService
   * @param {ZaakService} zaakService
   */
  constructor(
    private modalService: ModalService,
    private snackbarService: SnackbarService,
    private zaakService: ZaakService,
  ) {
  }

  //
  // Angular lifecycle.
  //

  ngOnInit(): void {
    this.form = this.getForm();
  }

  //
  // Context.
  //

  /**
   * Returns the field configurations for the form..
   */
  getForm(): FieldConfiguration[] {
    return [
      {
        label: 'Identificatie',
        name: 'relation_zaak',
        required: true,
        choices: [],
        onSearch: this.updateZaakChoices.bind(this)
      },
      {
        label: 'Aard relatie',
        name: 'aard_relatie',
        required: true,
        choices: this.AARD_RELATIES
      },
      {
        label: 'Aard relatie (omgekeerd)',
        name: 'aard_relatie_omgekeerde_richting',
        required: true,
        choices: this.AARD_RELATIES,
        value: 'onderwerp',
      },
      {
        name: 'main_zaak',
        type: 'hidden',
        value: this.mainZaakUrl,
      },
    ]
  }

  /**
   * Updates the zaak (case) selector field (field) with choices based on input.
   * @param {string} identificatie (Partial) identificatie of zaak (case).
   * @param {Field} field
   */
  updateZaakChoices(identificatie: string, field: Field): void {
    if(!identificatie) {
      return
    }

    this.zaakService.searchZaken(identificatie).subscribe(
      (zaken: Zaak[]) => {
        const choices = zaken.map((zaak: Zaak) => ({value: zaak.url, label: zaak.identificatie}));
        return field.choices = choices;
      },
      this.reportError.bind(this)
    )
  }

  //
  // Events.
  //

  submitForm(formData): void {
    this.isLoading = true;
    this.zaakService.addRelatedCase(formData).subscribe(() => {
      this.reload.emit(true);
      this.modalService.close("gerelateerde-zaken-modal");
      this.isLoading = false;
    }, this.reportError.bind(this))
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
    this.isLoading = false;
  }
}
