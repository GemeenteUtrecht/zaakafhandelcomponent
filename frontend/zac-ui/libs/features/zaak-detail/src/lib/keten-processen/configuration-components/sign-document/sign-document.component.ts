import { Component } from '@angular/core';

@Component({
  selector: 'gu-sign-document',
  templateUrl: './sign-document.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class SignDocumentComponent {

  steps = 1;
  minDate = new Date();

  dropdownSettings = {
    singleSelection: true,
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
    document.querySelector(`#configuration-select--${index}`).remove();
  }

}
