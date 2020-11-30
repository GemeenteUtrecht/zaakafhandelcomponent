import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApprovalComponent } from './approval/approval.component';
import { AdviceComponent } from './advice/advice.component';
import { FeaturesKownslComponent } from './features-kownsl.component';
import { FeaturesKownslRoutingModule } from './features-kownsl-routing.module';

@NgModule({
  imports: [
    CommonModule,
    FeaturesKownslRoutingModule
  ],
  declarations: [
    ApprovalComponent,
    AdviceComponent,
    FeaturesKownslComponent
  ]
})
export class FeaturesKownslModule {}
