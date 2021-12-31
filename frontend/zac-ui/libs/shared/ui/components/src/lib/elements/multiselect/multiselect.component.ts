import { AfterContentInit, Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormBuilder, FormControl } from '@angular/forms';

/**
 * <gu-multiselect [control]="formControl" [items]="items" label="Multiselect"></gu-multiselect>
 *
 * Generic multiselect component. Based on ng-select.
 *
 * Requires control: Reactive Form Control
 * Requires items: Array of objects
 *
 * Takes bindLabel: Key for the option label
 * Takes bindValue: Key for the option value
 * Takes multiple: Allow multiple selections
 * Takes placeholder: Placeholder for the field
 * Takes required: Sets required for form
 * Takes searchable: Allow user to type and search
 * Takes selectedValue: Pre selected values
 * Takes label: Label of the input field
 * Takes appendTo: HTML class to append the dropdown to
 *
 * Emits search: Fires an event when the users types
 * Emits change: Fires an event when an option is selected
 *
 */
@Component({
  selector: 'gu-multiselect',
  templateUrl: './multiselect.component.html',
  styleUrls: ['./multiselect.component.scss'],
})
export class MultiselectComponent implements OnInit, AfterContentInit {
  @Input() control: FormControl;
  @Input() items = [];

  @Input() bindLabel = 'name';
  @Input() bindValue = 'id'
  @Input() multiple: boolean;
  @Input() placeholder: string;
  @Input() required: boolean
  @Input() searchable = true;
  @Input() selectedValue: any;
  @Input() label: string;
  @Input() appendTo: string;
  @Input() clearable = true;

  @Output() search: EventEmitter<any> = new EventEmitter<any>();
  @Output() change: EventEmitter<any> = new EventEmitter<any>();

  selectedItems: any;

  constructor(private fb: FormBuilder) {}

  /**
   * Angular lifecycle hook.
   */
  ngOnInit() {
    if (!this.control) {
      this.control = this.fb.control('')
    }
  }

  /**
   * Angular lifecycle hook.
   */
  ngAfterContentInit() {
    if (this.selectedValue) {
      this.selectedItems = this.selectedValue
    }
  }

  /**
   * Emits value if the user uses the search field.
   * @param value
   */
  onSearch(value){
    this.search.emit(value.term);
  }

  /**
   * Emits the value after an option selection.
   * @param value
   */
  onChange(value){
    this.change.emit(value);
  }
}
