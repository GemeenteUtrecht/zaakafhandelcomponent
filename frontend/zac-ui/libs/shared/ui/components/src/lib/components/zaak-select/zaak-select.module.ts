import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {MultiselectModule, SharedUiComponentsModule} from '@gu/components';
import {ZaakSelectComponent} from './zaak-select.component';


@NgModule({
  imports: [
    CommonModule,
    MultiselectModule,
    SharedUiComponentsModule,
  ],
  exports: [
    ZaakSelectComponent,
  ]
})
export class ZaakSelectModule {
}
