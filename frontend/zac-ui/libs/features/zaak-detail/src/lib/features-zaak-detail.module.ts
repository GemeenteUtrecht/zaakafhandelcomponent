import {CommonModule} from '@angular/common';
import {HttpClientModule, HttpClientXsrfModule} from '@angular/common/http';
import {NgModule} from '@angular/core';
import {RouterModule} from '@angular/router';
import {FormGroupDirective, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {TabsModule} from 'ngx-bootstrap/tabs';
import {MultiselectModule, SharedUiComponentsModule} from '@gu/components';
import {FeaturesSearchModule} from '@gu/search';
import {ActiviteitenComponent} from './actions/activiteiten/activiteiten.component';
import {KownslSummaryComponent} from './actions/adviseren-accorderen/kownsl-summary.component';
import {DetailModalComponent} from './actions/adviseren-accorderen/detail-modal/detail-modal.component';
import {BetrokkenenComponent} from './overview/betrokkenen/betrokkenen.component';
import {DocumentenModule} from './documenten/documenten.module';
import {FeaturesZaakDetailComponent} from './features-zaak-detail.component';
import {GerelateerdeObjectenComponent} from './gerelateerde-objecten/gerelateerde-objecten.component';
import {GerelateerdeZakenModule} from './overview/gerelateerde-zaken/gerelateerde-zaken.module';
import {InformatieComponent} from './overview/informatie/informatie.component';
import {KetenProcessenModule} from './actions/keten-processen/keten-processen.module';
import {StatusComponent} from './actions/status/status.component';
import {ToegangVerlenenComponent} from './overview/toegang-verlenen/toegang-verlenen.component';
import {ZaakMapComponent} from './gerelateerde-objecten/zaak-map/zaak-map.component';
import {UserPermissionsComponent} from './overview/user-permissions/user-permissions.component';
import {TaskHistoryComponent} from './actions/task-history/task-history.component';
import {ChecklistComponent} from './actions/checklist/checklist.component';
import {CancelReviewComponent} from './actions/adviseren-accorderen/cancel-review/cancel-review.component';
import { MatExpansionModule } from '@angular/material/expansion';
import { RemindReviewComponent } from './actions/adviseren-accorderen/remind-review/remind-review.component';

@NgModule({
  imports: [
    CommonModule,
    DocumentenModule,
    FormsModule,
    GerelateerdeZakenModule,
    HttpClientModule,
    HttpClientXsrfModule.withOptions({
      cookieName: 'csrftoken',
      headerName: 'X-CSRFToken',
    }),
    KetenProcessenModule,
    MatExpansionModule,
    MultiselectModule,
    ReactiveFormsModule,
    RouterModule,
    FeaturesSearchModule,
    SharedUiComponentsModule,
    TabsModule.forRoot(),
  ],
  declarations: [
    ActiviteitenComponent,
    KownslSummaryComponent,
    BetrokkenenComponent,
    ChecklistComponent,
    DetailModalComponent,
    FeaturesZaakDetailComponent,
    GerelateerdeObjectenComponent,
    InformatieComponent,
    StatusComponent,
    TaskHistoryComponent,
    ToegangVerlenenComponent,
    UserPermissionsComponent,
    ZaakMapComponent,
    CancelReviewComponent,
    RemindReviewComponent,
  ],
  exports: [FeaturesZaakDetailComponent],
  providers: [FormGroupDirective]
})
export class FeaturesZaakDetailModule {
}
