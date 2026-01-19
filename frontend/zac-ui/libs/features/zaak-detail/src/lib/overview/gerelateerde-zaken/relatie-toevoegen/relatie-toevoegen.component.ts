import {
  Component,
  Input,
  OnInit,
  Output,
  EventEmitter,
} from '@angular/core';
import {Choice, Field, FieldConfiguration, ModalService, SnackbarService} from '@gu/components';
import {Zaak} from '@gu/models';
import {ZaakService} from '@gu/services';

@Component({
  selector: 'gu-relatie-toevoegen',
  templateUrl: './relatie-toevoegen.component.html',
  styleUrls: ['./relatie-toevoegen.component.scss'],

})
export class RelatieToevoegenComponent implements OnInit {
  @Input() mainZaakUrl: string;
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();

  form: FieldConfiguration[];
  isLoading: boolean;
  resultData: Zaak[] = [];
  resultLength: number;
  selectedTabIndex = -1;

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
   * Returns the field configurations for the form.
   * @param {Zaak} zaak If given, preselect zaak.
   */
  getForm(zaak: Zaak = null): FieldConfiguration[] {
    return [
      {
        label: 'Identificatie',
        name: 'bijdragezaak',
        required: true,
        choices: (zaak) ? [{value: zaak.url, label: zaak.identificatie}] : [],
        onChange: this.updateZaakValue.bind(this),
        onSearch: this.updateZaakChoices.bind(this),
        value: (zaak) ? zaak.url : null,
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
        name: 'hoofdzaak',
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
    if (!identificatie) {
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

  /**
   * NOTE: SV 2022-09-29 - There is a bug with multiselect not showing value in certain cases, probably after a form
   * re-render.
   *
   * I strongly think that multiselect stores its value as a string instead of a choice (object) which causes the widget
   * not to find the correct choice and lists its value. We can try to fix this in the future but this would likely
   * cause issues with other parts of the codebase directly reading the value.
   *
   * For now I worked around this by updating the choice value on the change volue on the change event, however in the
   * future we can try to have form (component) keep this in sync.
   *
   * As I update the value in this method, submitForm should be updated as well.
   *
   * @param {string} value
   * @param {Field} field
   */
  updateZaakValue(value: string, field: Field): void {
    // @ts-ignore
    field.control.value = value;
  }

  //
  // Events.
  //

  /**
   * Gets called when search results are loaded.
   * @param {Zaak[]} results
   */
  onLoadResult(results: Zaak[]) {
    this.resultData = results;
  }

  /**
   * Gets called on result length.
   * @param data
   */
  onResultLength(data): void {
    this.resultLength = data;
  }

  /**
   * Gets called when a zaak (case) is selected from search results.
   * @param {Zaak} zaak
   */
  onTableOutput(zaak: Zaak) {
    this.selectedTabIndex = 0;
    this.form = null;
    setTimeout(() => {
      this.form = this.getForm(zaak);
    });
  }

  /**
   * Gets called when the form is submitted.
   * @param {Object} formData
   */
  submitForm(formData): void {
    // Update due to change to value format.
    formData.bijdragezaak = (typeof formData.bijdragezaak === 'string')
      ? formData.bijdragezaak
      : formData.bijdragezaak?.value;

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
    const message = error?.error?.detail || error?.error.nonFieldErrors?.join(', ') || this.errorMessage;
    this.snackbarService.openSnackBar(message, 'Sluiten', 'warn');
    console.error(error);
    this.isLoading = false;
  }
}
