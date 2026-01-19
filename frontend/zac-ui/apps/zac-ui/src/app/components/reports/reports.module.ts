import { CUSTOM_ELEMENTS_SCHEMA, NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReportsRoutingModule } from './reports-routing.module';
import { ReportsComponent } from './reports.component';
import { FeaturesReportsModule } from '@gu/reports';

@NgModule({
  declarations: [ReportsComponent],
  imports: [CommonModule, ReportsRoutingModule, FeaturesReportsModule],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
})
export class ReportsModule {}
