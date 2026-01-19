import { NgModule, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ZakenComponent } from './zaken.component';
import { ZaakDetailComponent } from './zaak-detail/zaak-detail.component'

import { FeaturesZaakDetailModule } from '@gu/zaak-detail';
import { ZakenRoutingModule } from './zaken-routing.module';
import { CollapseModule } from 'ngx-bootstrap/collapse';
import { FeaturesSearchModule } from '@gu/search';
import { SharedUiComponentsModule } from '@gu/components';
import { TabsModule } from 'ngx-bootstrap/tabs';


@NgModule({
  declarations: [
    ZakenComponent,
    ZaakDetailComponent
  ],
  imports: [
    CommonModule,
    FeaturesSearchModule,
    ZakenRoutingModule,
    FeaturesZaakDetailModule,
    CollapseModule,
    SharedUiComponentsModule,
    TabsModule.forRoot(),
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class ZakenModule { }
