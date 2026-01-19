import {
  AfterContentInit,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  Output,
  ViewChild
} from '@angular/core';
import {UntypedFormBuilder, UntypedFormControl} from '@angular/forms';
import { NgSelectComponent } from '@ng-select/ng-select';

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
 * Takes searchable: Allow user
 * to type and search
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
export class MultiselectComponent implements OnInit, OnChanges, OnDestroy {
  @ViewChild('multiselect') select: NgSelectComponent;

  @Input() control: UntypedFormControl;
  @Input() items = [];

  @Input() bindLabel = 'name';
  @Input() bindValue = 'id'
  @Input() multiple: boolean;
  @Input() placeholder: string;
  @Input() required: boolean
  @Input() searchable = true;
  @Input() selectedValue: any;
  @Input() label: string;
  @Input() appendTo? = 'body';
  @Input() clearable = true;
  @Input() disabled: boolean;
  @Input() error: boolean;
  @Input() widgetType: 'checkboxGroup' | 'select' = 'select';

  @Output() search: EventEmitter<any> = new EventEmitter<any>();
  @Output() change: EventEmitter<any> = new EventEmitter<any>();

  selectedItems: string[];

  /**
   * Constructor method.
   * @param {FormBuilder} fb
   */
  constructor(private fb: UntypedFormBuilder) {
  }


  //
  // Getters / setters.
  //

  /**
   * Returns whether all items are checked (for widgetType === 'checkboxGroup').
   * @return {boolean}
   */
  getAllChecked(): boolean {
    if(this.widgetType !== 'checkboxGroup' || !this.selectedItems) {
      return false;
    }

    return this.items.every((item) => this.selectedItems.indexOf(item[this.bindValue]) > -1);
  }

  /**
   * Returns whether an item should be checked (for widgetType === 'checkboxGroup').
   * @param {Object} item
   * @return {boolean}
   */
  getIsChecked(item: any): boolean {
    return this.selectedItems?.indexOf(item[this.bindValue]) > -1;
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    if (!this.control) {
      this.control = this.fb.control('')
    }
    window.addEventListener('scroll', this.onScroll, true);
  }

  ngOnDestroy() {
    window.removeEventListener('scroll', this.onScroll, true);
  }

  /**
   * A lifecycle hook that is called when any data-bound property of a directive changes. Define an ngOnChanges() method
   * to handle the changes.
   */
  ngOnChanges(): void {
    if (this.selectedValue) {
      this.selectedItems = this.selectedValue
    }
  }

  //
  // Events.
  //

  private onScroll = (event: any) => {
    if (this.select && this.select.isOpen) {
      const isScrollingInScrollHost = (event.target.className as string).indexOf('ng-dropdown-panel-items') > -1;
      if (isScrollingInScrollHost) { return; }
      this.select.dropdownPanel.adjustPosition();

    }
  }

  /**
   * Emits value if the user uses the search field.
   * @param value
   */
  onSearch(value: any): void {
    this.search.emit(value.term);
  }

  /**
   * Emits the value after an option selection.
   * @param value
   */
  onChange(value: any): void {
    this.change.emit(value);
  }

  /**
   * Gets called when the checkbox group selection changed.
   * @param {Event} event
   */
  onCheckboxGroupChange(event: Event) {
    event.stopPropagation();

    const groupElement = event.currentTarget as HTMLElement;
    const selectedCheckboxes = groupElement.querySelectorAll('input:checked');

    this.selectedItems = Array.from(selectedCheckboxes)
      .filter((checkbox: HTMLInputElement) => !checkbox.classList.contains('multiselect__select-all'))
      .map((checkbox: HTMLInputElement) => checkbox.value);

    const value = this.items.filter((item) => this.selectedItems.indexOf(item[this.bindValue]) > -1);
    this.control.setValue(this.selectedItems)

    this.onChange(value);
  }

  /**
   * Gets called when check all toggle is clicked.
   */
  toggleCheckAll() {
    if(this.getAllChecked()) {
      this.selectedItems = []
    } else {
      this.selectedItems = this.items.map((item) => item[this.bindValue]);
    }
    const value = this.items.filter((item) => this.selectedItems.indexOf(item[this.bindValue]) > -1);
    this.control.setValue(this.selectedItems)

    this.onChange(value);
  }

  /**
   * Allows the use of objects as bindValue
   * @param item
   * @param selected
   * @returns {boolean}
   */
  compareWith(item, selected) {
    return item.value?.omschrijving
      ? item.value.omschrijving === selected.omschrijving
      : item[this.bindValue] === selected;
  }
}
