import { NgModule } from '@angular/core';
import { CommonModule, TitleCasePipe } from '@angular/common';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import {FeaturesLandingComponent} from './features-landing.component';
import { NgSelectModule } from '@ng-select/ng-select';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { FilterResultsPipe } from './landing.pipe';
import { SharedUtilsModule } from '@gu/utils';

@NgModule({
  imports: [CommonModule, MultiselectModule, NgSelectModule, SharedUiComponentsModule, FormsModule, RouterModule, MatButtonToggleModule, ReactiveFormsModule, SharedUtilsModule],
  declarations: [FeaturesLandingComponent, FilterResultsPipe],
  exports: [FeaturesLandingComponent],
  providers: [TitleCasePipe]
})
export class FeaturesLandingModule {}
