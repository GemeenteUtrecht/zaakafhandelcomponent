import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {FeaturesFormsComponent} from "./features-forms.component";
import {SharedUiComponentsModule} from "@gu/components";

@NgModule({
  imports: [CommonModule, SharedUiComponentsModule],
  exports: [FeaturesFormsComponent],
  declarations: [FeaturesFormsComponent],
})
export class FeaturesFormsModule {
}
