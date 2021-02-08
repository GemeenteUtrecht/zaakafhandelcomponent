import { Component } from '@angular/core';

@Component({
  selector: 'gu-config-adviseren-accorderen',
  templateUrl: './adviseren-accorderen.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class AdviserenAccorderenComponent {

  steps = 1;
  minDate = new Date();
  items= [
    {
      name: "John",
      id: "John"
    },
    {
      name: "Mike",
      id: "Mike"
    },
    {
      name: "Lisa",
      id: "Lisa"
    },
  ]

  constructor() { }

  addStep() {
    this.steps++
  }

  deleteStep(index) {
    this.steps--
    document.querySelector(`#configuration-multiselect--${index}`).remove();
  }

}
