import { Component, ElementRef, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { FormControl } from '@angular/forms';
import { COMMA, ENTER } from '@angular/cdk/keycodes';
import { map, startWith } from 'rxjs/operators';
import { Observable } from 'rxjs';
import { MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { MatChipInputEvent } from '@angular/material/chips';
import { User } from '@gu/models';

@Component({
  selector: 'gu-autocomplete',
  templateUrl: './autocomplete.component.html',
  styleUrls: ['./autocomplete.component.scss']
})
export class AutocompleteComponent implements OnInit {
  @Input() control: FormControl;
  @Input() selectable: boolean;
  @Input() removable: boolean;
  @Input() type: string;
  @Input() label: string;
  @Input() required: boolean;
  @Input() disabled: boolean;
  @Input() placeholder: string;
  @Input() multiple: boolean;
  @Input() fullWidth: boolean;

  @Input() bindLabel: string;
  @Input() bindValue: string;

  @Output() onChange: EventEmitter<any> = new EventEmitter<any>();

  separatorKeysCodes: number[] = [ENTER, COMMA];
  filteredOptions: Observable<object[]>;

  @Input () options: object[];

  @ViewChild('guInput') guInput: ElementRef<HTMLInputElement>;

  constructor() {}

  ngOnInit() {
    this.filteredOptions = this.control.valueChanges
      .pipe(
        startWith(''),
        map(value => typeof value === 'string' ? value : value[this.bindLabel]),
        map(label => label ? this.filterOptions(label) : this.options.slice())
      );

  }

  add(event: MatChipInputEvent): void {
    const value = event.value;

    // Add our fruit
    if (value) {
      // this.options.push(value);
    }

    // Clear the input value
    // event.input!.clear();

    this.control.setValue(null);
  }

  remove(option: object): void {
    const index = this.options.indexOf(option);

    if (index >= 0) {
      this.options.splice(index, 1);
    }
  }

  selected(event: MatAutocompleteSelectedEvent): void {
    // this.options.push(event.option.viewValue);
    console.log(event.option.viewValue);
    // this.guInput.nativeElement.value = '';
    // this.control.setValue(null);
    // this.onChange.emit(true)
  }

  filterOptions(label: string): any[] {
    const filterLabel = label.toLowerCase();
    return this.options.filter(item => item[this.bindLabel].toLowerCase().includes(filterLabel));
  }

  displayFn(option: object): string {
    console.log(option);
    console.log(this.bindValue);
    console.log(option[this.bindLabel]);
    return option ? option[this.bindLabel] : option;
  }

  returnFn(option: object): number | undefined {
    return option ? option[this.bindValue] : undefined;
  }

  /**
   * Creates input label.
   * @returns {string}
   */
  getLabel() {
    return this.required ? this.label : (this.label + ' (niet verplicht)')
  }
}
