import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { ZakenComponent } from './zaken.component';
import { ZaakDetailComponent } from './zaak-detail/zaak-detail.component';

const routes: Routes = [
  {
    path: '',
    component: ZakenComponent
  },
  {
    path: ':bronorganisatie/:identificatie',
    redirectTo: ':bronorganisatie/:identificatie/overzicht'
  },
  {
    path: ':bronorganisatie/:identificatie/:tabId',
    component: ZaakDetailComponent
  }
];

/**
 * Module responsible for routing to component.
 */
@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ZakenRoutingModule {
}
