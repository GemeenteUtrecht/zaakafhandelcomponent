import { NgModule, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ZaakDetailComponent } from './zaak-detail.component'
import { FeaturesZaakDetailModule } from '@gu/zaak-detail';
import { ZaakDetailRoutingModule } from './zaak-detail-routing.module';



@NgModule({
  declarations: [
    ZaakDetailComponent,
  ],
  imports: [
    CommonModule,
    ZaakDetailRoutingModule,
    FeaturesZaakDetailModule
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class ZaakDetailModule { }
