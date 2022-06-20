import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {FeaturesFormsComponent} from "./features-forms.component";
import {SharedUiComponentsModule} from "@gu/components";
import { CreateCaseComponent } from './create-case/create-case.component';

@NgModule({
  imports: [CommonModule, SharedUiComponentsModule],
  exports: [FeaturesFormsComponent],
  declarations: [FeaturesFormsComponent, CreateCaseComponent],
})
export class FeaturesFormsModule {
}
