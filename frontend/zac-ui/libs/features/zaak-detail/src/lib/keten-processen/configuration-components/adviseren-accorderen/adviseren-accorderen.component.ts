import { Component } from '@angular/core';

@Component({
  selector: 'gu-config-adviseren-accorderen',
  templateUrl: './adviseren-accorderen.component.html',
  styleUrls: ['./adviseren-accorderen.component.scss']
})
export class AdviserenAccorderenComponent {

  steps = 1;
  minDate = new Date();

  constructor() { }

  addStep() {
    this.steps++
  }

  deleteStep(index) {
    this.steps--
    document.querySelector(`#configuration-multiselect--${index}`).remove();
  }

}
