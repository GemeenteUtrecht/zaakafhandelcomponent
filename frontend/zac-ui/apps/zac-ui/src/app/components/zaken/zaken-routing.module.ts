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
    component: ZaakDetailComponent
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ZakenRoutingModule {
}
