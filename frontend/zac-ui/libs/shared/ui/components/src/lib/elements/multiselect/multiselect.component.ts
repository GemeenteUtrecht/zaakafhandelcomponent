import { AfterContentInit, AfterViewInit, Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormBuilder, FormControl } from '@angular/forms';

@Component({
  selector: 'gu-multiselect',
  templateUrl: './multiselect.component.html',
  styleUrls: ['./multiselect.component.scss'],
})
export class MultiselectComponent implements OnInit, AfterContentInit {
  @Input() placeholder: string;
  @Input() items = [];
  @Input() bindLabel = 'name';
  @Input() bindValue = 'id'
  @Input() multiple: boolean;
  @Input() control: FormControl;
  @Input() required: boolean
  @Input() searchable = true;
  @Input() selectedValue: any;
  @Input() label: string;

  @Output() search: EventEmitter<any> = new EventEmitter<any>();
  @Output() change: EventEmitter<any> = new EventEmitter<any>();

  selectedItems: any;

  constructor(private fb: FormBuilder) {}

  ngOnInit() {
    if (!this.control) {
      this.control = this.fb.control('')
    }
  }

  ngAfterContentInit() {
    if (this.selectedValue) {
      this.selectedItems = this.selectedValue
    }
  }

  onSearch(value){
    this.search.emit(value.term);
  }

  onChange(value){
    this.change.emit(value);
  }
}
