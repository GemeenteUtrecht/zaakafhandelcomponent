import { Component } from '@angular/core';

@Component({
  selector: 'gu-sign-document',
  templateUrl: './sign-document.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class SignDocumentComponent {

  steps = 1;
  minDate = new Date();


  constructor() { }

  addStep() {
    this.steps++
  }

  deleteStep(index) {
    this.steps--
    document.querySelector(`#configuration-select--${index}`).remove();
  }

}
