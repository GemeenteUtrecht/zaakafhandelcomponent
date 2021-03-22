import { Component } from '@angular/core';
import { Zaak } from '@gu/models';

@Component({
  selector: 'gu-features-search',
  templateUrl: './features-search.component.html',
  styleUrls: ['./features-search.component.scss']
})
export class FeaturesSearchComponent {

  resultData: Zaak[];

  constructor() { }

  setResult(resultData: Zaak[]) {
    this.resultData = resultData;
  }
}
