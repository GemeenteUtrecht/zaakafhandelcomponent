import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { ZaakDetailComponent } from './zaak-detail.component';

const routes: Routes = [
  {
    path: '',
    component: ZaakDetailComponent,
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ZaakDetailRoutingModule { }
