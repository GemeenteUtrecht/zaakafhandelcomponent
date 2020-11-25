import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApprovalComponent } from './approval/approval.component';
import { AdviceComponent } from './advice/advice.component';
import { FeaturesKownslComponent } from './features-kownsl.component';

@NgModule({
  imports: [CommonModule],
  declarations: [ApprovalComponent, AdviceComponent, FeaturesKownslComponent],
  exports: [FeaturesKownslComponent]
})
export class FeaturesKownslModule {}
