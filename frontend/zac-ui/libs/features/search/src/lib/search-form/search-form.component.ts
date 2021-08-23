import {Component, EventEmitter, Input, Output} from '@angular/core';
import {Zaak, TableSort} from '@gu/models';


/**
 * This component allows the user to search Zaken dynamically.
 * Selecting a zaaktype will show its corresponding properties,
 * which can be chosen to further refine the search query.
 *
 * The user can also save the given search input as a report by
 * selecting the checkbox and give te report a name.
 */
@Component({
  selector: 'gu-search-form',
  templateUrl: './search-form.component.html',
  styleUrls: ['./search-form.component.scss']
})
export class SearchFormComponent {
  @Input() sortData: TableSort;
  @Output() loadResult: EventEmitter<Zaak[]> = new EventEmitter<Zaak[]>();
}
