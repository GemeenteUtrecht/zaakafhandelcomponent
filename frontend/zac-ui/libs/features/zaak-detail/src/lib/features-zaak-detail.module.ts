import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FeaturesZaakDetailComponent } from './features-zaak-detail.component';
import { SharedUiComponentsModule } from '@gu/components';
import { InformatieComponent } from './informatie/informatie.component';
import { BetrokkenenComponent } from './betrokkenen/betrokkenen.component';
import { StatusComponent } from './status/status.component';
import { GerelateerdeZakenComponent } from './gerelateerde-zaken/gerelateerde-zaken.component';
import { GerelateerdeObjectenComponent } from './gerelateerde-objecten/gerelateerde-objecten.component';
import { DocumentenComponent } from './documenten/documenten.component';
import { AdviserenAccorderenComponent } from './adviseren-accorderen/adviseren-accorderen.component';
import { KetenProcessenModule } from './keten-processen/keten-processen.module';
import { FormGroupDirective, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';

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
  ],
  declarations: [
    FeaturesZaakDetailComponent,
    InformatieComponent,
    BetrokkenenComponent,
    StatusComponent,
    GerelateerdeZakenComponent,
    GerelateerdeObjectenComponent,
    DocumentenComponent,
    AdviserenAccorderenComponent
  ],
  exports: [FeaturesZaakDetailComponent],
  providers: [FormGroupDirective]
})
export class FeaturesZaakDetailModule {}
