import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { KownslComponent } from './kownsl.component';

import { KownslRoutingModule } from './kownsl-routing.module';
import { SharedUiComponentsModule } from '@gu/components';

@NgModule({
  declarations: [KownslComponent],
  imports: [
    CommonModule,
    KownslRoutingModule,
    SharedUiComponentsModule
  ],
  exports: [
    KownslComponent
  ]
})
export class KownslModule { }
