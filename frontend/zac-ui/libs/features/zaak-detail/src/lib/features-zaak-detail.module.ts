import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FeaturesZaakDetailComponent } from './features-zaak-detail.component';
import { SharedUiComponentsModule } from '@gu/components';
import { InformatieComponent } from './informatie/informatie.component';
import { BetrokkenenComponent } from './betrokkenen/betrokkenen.component';
import { StatusComponent } from './status/status.component';
import { GerelateerdeObjectenComponent } from './gerelateerde-objecten/gerelateerde-objecten.component';
import { AdviserenAccorderenComponent } from './adviseren-accorderen/adviseren-accorderen.component';
import { KetenProcessenModule } from './keten-processen/keten-processen.module';
import { FormGroupDirective, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';
import { GerelateerdeZakenModule } from './gerelateerde-zaken/gerelateerde-zaken.module';
import { DocumentenModule } from './documenten/documenten.module';
import { DetailModalComponent } from './adviseren-accorderen/detail-modal/detail-modal.component';

@NgModule({
  imports: [
    CommonModule,
    HttpClientModule,
    HttpClientXsrfModule.withOptions({
      cookieName: 'csrftoken',
      headerName: 'X-CSRFToken',
    }),
    FormsModule,
    ReactiveFormsModule,
    SharedUiComponentsModule,
    KetenProcessenModule,
    GerelateerdeZakenModule,
    DocumentenModule
  ],
  declarations: [
    FeaturesZaakDetailComponent,
    InformatieComponent,
    BetrokkenenComponent,
    StatusComponent,
    GerelateerdeObjectenComponent,
    AdviserenAccorderenComponent,
    DetailModalComponent
  ],
  exports: [FeaturesZaakDetailComponent],
  providers: [FormGroupDirective]
})
export class FeaturesZaakDetailModule {}
