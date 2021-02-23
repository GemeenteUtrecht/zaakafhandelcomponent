import { Component, OnInit } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { FeaturesSearchService } from './features-search.service';
import { Zaak } from '@gu/models';

@Component({
  selector: 'gu-features-search',
  templateUrl: './features-search.component.html',
  styleUrls: ['./features-search.component.scss']
})
export class FeaturesSearchComponent implements OnInit {

  resultData: Zaak[];

  constructor(
    private fb: FormBuilder,
    private searchService: FeaturesSearchService
  ) { }

  ngOnInit(): void {
  }

  setResult(resultData: Zaak[]) {
    this.resultData = resultData;
  }
}
