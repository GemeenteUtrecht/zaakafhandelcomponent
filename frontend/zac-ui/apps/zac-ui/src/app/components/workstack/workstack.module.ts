import { CUSTOM_ELEMENTS_SCHEMA, NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { WorkstackRoutingModule } from './workstack-routing.module';
import { WorkstackComponent } from './workstack.component';
import { FeaturesWorkstackModule } from '@gu/workstack';

@NgModule({
  declarations: [WorkstackComponent],
  imports: [
    CommonModule,
    WorkstackRoutingModule,
    FeaturesWorkstackModule
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class WorkstackModule { }
