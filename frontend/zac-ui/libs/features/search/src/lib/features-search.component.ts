import { Component } from '@angular/core';
import { TableSort, Zaak } from '@gu/models';
import { PageEvent } from '@angular/material/paginator';

@Component({
  selector: 'gu-features-search',
  templateUrl: './features-search.component.html',
  styleUrls: ['./features-search.component.scss']
})
export class FeaturesSearchComponent {

  resultData: Zaak[];
  resultLength: number;
  sortData: TableSort;
  pageData: PageEvent;

}
