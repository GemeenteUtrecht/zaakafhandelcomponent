import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormControl } from '@angular/forms';

@Component({
  selector: 'gu-multiselect',
  templateUrl: './multiselect.component.html',
  styleUrls: ['./multiselect.component.scss'],
})
export class MultiselectComponent implements OnInit {
  @Input() placeholder: string;
  @Input() items = [];
  @Input() bindLabel = 'name';
  @Input() bindValue = 'id'
  @Input() multiple: boolean;
  @Input() control: FormControl;
  @Input() required: boolean
  @Input() searchable = true;
  @Input() selectedValue: any;

  @Output() typeOutput: EventEmitter<any> = new EventEmitter<any>();

  selectedItems: any;

  constructor() {}

  ngOnInit() {
    if (this.selectedValue) {
      this.selectedItems = this.selectedValue
    }
  }

  onSearch(value){
    this.typeOutput.emit(value.term);
  }
}
