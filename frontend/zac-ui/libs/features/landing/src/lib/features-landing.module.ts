import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import {SharedUiComponentsModule} from '@gu/components';
import {FeaturesLandingComponent} from './features-landing.component';

@NgModule({
  imports: [CommonModule, SharedUiComponentsModule],
  declarations: [FeaturesLandingComponent],
  exports: [FeaturesLandingComponent]
})
export class FeaturesLandingModule {}
