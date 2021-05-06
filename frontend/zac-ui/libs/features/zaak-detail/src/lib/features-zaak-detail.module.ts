import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormGroupDirective, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';

import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';

import { FeaturesZaakDetailComponent } from './features-zaak-detail.component';
import { InformatieComponent } from './informatie/informatie.component';
import { BetrokkenenComponent } from './betrokkenen/betrokkenen.component';
import { StatusComponent } from './status/status.component';
import { GerelateerdeObjectenComponent } from './gerelateerde-objecten/gerelateerde-objecten.component';
import { AdviserenAccorderenComponent } from './adviseren-accorderen/adviseren-accorderen.component';
import { KetenProcessenModule } from './keten-processen/keten-processen.module';
import { GerelateerdeZakenModule } from './gerelateerde-zaken/gerelateerde-zaken.module';
import { DocumentenModule } from './documenten/documenten.module';
import { DetailModalComponent } from './adviseren-accorderen/detail-modal/detail-modal.component';
import { ToegangVerlenenComponent } from './toegang-verlenen/toegang-verlenen.component';
import { ActiviteitenComponent } from './activiteiten/activiteiten.component';
import { TabsModule } from 'ngx-bootstrap/tabs';

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
    DocumentenModule,
    MultiselectModule,
    TabsModule.forRoot()
  ],
  declarations: [
    FeaturesZaakDetailComponent,
    InformatieComponent,
    BetrokkenenComponent,
    StatusComponent,
    GerelateerdeObjectenComponent,
    AdviserenAccorderenComponent,
    DetailModalComponent,
    ToegangVerlenenComponent,
    ActiviteitenComponent,
  ],
  exports: [FeaturesZaakDetailComponent],
  providers: [FormGroupDirective]
})
export class FeaturesZaakDetailModule {}
