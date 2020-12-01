import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApprovalComponent } from './approval/approval.component';
import { AdviceComponent } from './advice/advice.component';
import { FeaturesKownslComponent } from './features-kownsl.component';
import { FeaturesKownslRoutingModule } from './features-kownsl-routing.module';

import { SharedUiComponentsModule } from '@gu/ui-components';

@NgModule({
  imports: [
    CommonModule,
    FeaturesKownslRoutingModule,
    SharedUiComponentsModule,
  ],
  declarations: [
    ApprovalComponent,
    AdviceComponent,
    FeaturesKownslComponent
  ]
})
export class FeaturesKownslModule {}
