import { Component } from '@angular/core';

@Component({
  selector: 'gu-config-adviseren-accorderen',
  templateUrl: './adviseren-accorderen.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class AdviserenAccorderenComponent {

  steps = 1;
  minDate = new Date();

  dropdownSettings = {
    singleSelection: false,
    idField: 'item_id',
    textField: 'item_text',
    selectAllText: 'Select All',
    unSelectAllText: 'UnSelect All',
    itemsShowLimit: 3,
    allowSearchFilter: true,
    enableCheckAll: false,
    searchPlaceholderText: 'Zoeken'
  };

  constructor() { }

  addStep() {
    this.steps++
  }

  deleteStep(index) {
    this.steps--
    document.querySelector(`#configuration-multiselect--${index}`).remove();
  }

}
