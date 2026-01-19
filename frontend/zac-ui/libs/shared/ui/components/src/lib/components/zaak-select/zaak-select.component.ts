import {Component, EventEmitter, Input, Output} from "@angular/core";
import {ZaakSearchService} from "./zaak-search.service";
import {UntypedFormControl} from "@angular/forms";

@Component({
  providers: [ZaakSearchService],
  selector: 'gu-zaak-select',
  styleUrls: ['./zaak-select.component.scss'],
  templateUrl: './zaak-select.component.html',
})
export class ZaakSelectComponent {
  @Input() control?: UntypedFormControl;
  @Input() label = 'Zaaknummer';
  @Input() placeholder? = '';
  @Input() appendTo? = 'body';

  @Output() search: EventEmitter<any> = new EventEmitter<any>();
  @Output() change: EventEmitter<any> = new EventEmitter<any>();

  choices: Array<{label: string, value: string}>;
  value: string;

  constructor(private zaakSearchService: ZaakSearchService) {}

  /**
   * Gets called whenever user enters text in them multiselect.
   * @param {string} query
   */
  onSearch(query) {
    if (query) {
      this.zaakSearchService.autocomplete(query).subscribe(
        (suggestions) => this.choices = this.zaakSearchService.suggestionsAsChoices(suggestions),
        (error) => console.error(error)
      );

      this.search.emit(query);
    }
  }

  /**
   * Gets called whenever the user select a suggestion.
   * @param choice
   */
  onChange(choice) {
    if (choice) {
      if (this.control) {
        this.control.setValue(choice.value);
      }

      this.change.emit(choice.value);
    }
  }
}
