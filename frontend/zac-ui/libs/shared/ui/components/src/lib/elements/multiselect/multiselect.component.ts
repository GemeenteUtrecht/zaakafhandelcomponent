import { Component, Input, OnInit } from '@angular/core';
import { IDropdownSettings } from 'ng-multiselect-dropdown';

@Component({
  selector: 'gu-multiselect',
  templateUrl: './multiselect.component.html',
  styleUrls: ['./multiselect.component.scss']
})
export class MultiselectComponent implements OnInit {
  dropdownList = [];
  selectedItems = [];

  @Input() dropdownSettings:IDropdownSettings = {};
  @Input() placeholder: string;
  constructor() { }

  ngOnInit(): void {
    this.dropdownList = [
      { item_id: 1, item_text: 'John' },
      { item_id: 2, item_text: 'Mike' },
      { item_id: 3, item_text: 'Lisa' }
    ];
  }
  onItemSelect(item: any) {
    console.log(item);
  }
  onSelectAll(items: any) {
    console.log(items);
  }
  typing() {
  }
}
