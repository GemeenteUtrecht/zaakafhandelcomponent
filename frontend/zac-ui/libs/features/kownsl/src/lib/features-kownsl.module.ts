import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { ApprovalComponent } from './approval/approval.component';
import { AdviceComponent } from './advice/advice.component';
import { FeaturesKownslComponent } from './features-kownsl.component';
import { FeaturesKownslRoutingModule } from './features-kownsl-routing.module';

// libs
import { SharedUiComponentsModule } from '@gu/components';

@NgModule({
  imports: [
    CommonModule,
    HttpClientModule,
    FormsModule,
    ReactiveFormsModule,
    FeaturesKownslRoutingModule,
    SharedUiComponentsModule,
  ],
  declarations: [
    ApprovalComponent,
    AdviceComponent,
    FeaturesKownslComponent
  ],
})
export class FeaturesKownslModule {}
