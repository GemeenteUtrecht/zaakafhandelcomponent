import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {MultiselectModule, SharedUiComponentsModule} from '@gu/components';
import {ZaakSelectComponent} from './zaak-select.component';
import {ZaakSearchService} from "./zaak-search.service";

@NgModule({
  imports: [
    CommonModule,
    MultiselectModule,
    SharedUiComponentsModule,
  ],
  declarations: [
    ZaakSelectComponent,
  ],
  exports: [
    ZaakSelectComponent,
  ]
})
export class ZaakSelectModule {
}
