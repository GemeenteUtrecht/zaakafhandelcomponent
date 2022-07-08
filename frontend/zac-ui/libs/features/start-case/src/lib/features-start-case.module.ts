import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {FeaturesStartCaseComponent} from "./features-start-case.component";
import {SharedUiComponentsModule} from "@gu/components";

@NgModule({
  imports: [CommonModule, SharedUiComponentsModule],
  exports: [FeaturesStartCaseComponent],
  declarations: [FeaturesStartCaseComponent],
})
export class FeaturesStartCaseModule {
}
