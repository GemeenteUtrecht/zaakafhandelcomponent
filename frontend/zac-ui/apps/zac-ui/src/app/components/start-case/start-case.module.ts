import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {SharedUiComponentsModule} from '@gu/components';
import {StartCaseRoutingModule} from './start-case-routing.module';
import {StartCaseComponent} from './start-case.component';
import {FeaturesStartCaseModule} from '@gu/start-case';

@NgModule({
  declarations: [StartCaseComponent],
  imports: [
    CommonModule,
    SharedUiComponentsModule,
    StartCaseRoutingModule,
    FeaturesStartCaseModule,
  ],
  exports: [
    StartCaseComponent
  ]
})
export class StartCaseModule {
}
