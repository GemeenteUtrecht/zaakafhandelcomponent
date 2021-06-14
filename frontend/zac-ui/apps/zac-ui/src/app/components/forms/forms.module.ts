import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {SharedUiComponentsModule} from '@gu/components';
import {FormsRoutingModule} from './forms-routing.module';
import {FormsComponent} from './forms.component';
import {FeaturesFormsModule} from "@gu/forms";

@NgModule({
  declarations: [FormsComponent],
  imports: [
    CommonModule,
    SharedUiComponentsModule,
    FormsRoutingModule,
    FeaturesFormsModule,
  ],
  exports: [
    FormsComponent
  ]
})
export class FormsModule {
}
