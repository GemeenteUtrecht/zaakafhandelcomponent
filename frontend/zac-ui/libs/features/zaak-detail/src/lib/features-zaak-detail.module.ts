import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FeaturesZaakDetailComponent } from './features-zaak-detail.component';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import { InformatieComponent } from './informatie/informatie.component';
import { BetrokkenenComponent } from './betrokkenen/betrokkenen.component';
import { StatusComponent } from './status/status.component';
import { KetenProcessenComponent } from './keten-processen/keten-processen.component';
import { GerelateerdeZakenComponent } from './gerelateerde-zaken/gerelateerde-zaken.component';
import { GerelateerdeObjectenComponent } from './gerelateerde-objecten/gerelateerde-objecten.component';
import { DocumentenComponent } from './documenten/documenten.component';
import { AdviserenAccorderenComponent } from './adviseren-accorderen/adviseren-accorderen.component';
import { KetenProcessenModule } from './keten-processen/keten-processen.module';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
// import { ModalModule } from '@gu/components';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    SharedUiComponentsModule,
    KetenProcessenModule,
    // ModalModule
  ],
  declarations: [
    FeaturesZaakDetailComponent,
    InformatieComponent,
    BetrokkenenComponent,
    StatusComponent,
    // KetenProcessenComponent,
    GerelateerdeZakenComponent,
    GerelateerdeObjectenComponent,
    DocumentenComponent,
    AdviserenAccorderenComponent
  ],
  exports: [FeaturesZaakDetailComponent]
})
export class FeaturesZaakDetailModule {}
