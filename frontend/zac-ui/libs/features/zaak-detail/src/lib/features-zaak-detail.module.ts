import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FeaturesZaakDetailComponent } from './features-zaak-detail.component';
import { SharedUiComponentsModule } from '@gu/components';
import { InformatieComponent } from './informatie/informatie.component';
import { BetrokkenenComponent } from './betrokkenen/betrokkenen.component';
import { StatusComponent } from './status/status.component';
import { KetenProcessenComponent } from './keten-processen/keten-processen.component';
import { GerelateerdeZakenComponent } from './gerelateerde-zaken/gerelateerde-zaken.component';
import { GerelateerdeObjectenComponent } from './gerelateerde-objecten/gerelateerde-objecten.component';
import { DocumentenComponent } from './documenten/documenten.component';

@NgModule({
  imports: [
    CommonModule,
    SharedUiComponentsModule,
  ],
  declarations: [
    FeaturesZaakDetailComponent,
    InformatieComponent,
    BetrokkenenComponent,
    StatusComponent,
    KetenProcessenComponent,
    GerelateerdeZakenComponent,
    GerelateerdeObjectenComponent,
    DocumentenComponent
  ],
  exports: [FeaturesZaakDetailComponent]
})
export class FeaturesZaakDetailModule {}
