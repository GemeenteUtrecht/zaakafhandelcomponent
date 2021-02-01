import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { HomeComponent } from './home/home.component';
import { ZaakDetailComponent } from './zaak-detail/zaak-detail.component';
import { ZaakDetailModule } from './zaak-detail/zaak-detail.module';

const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    component: HomeComponent,
  },
  {
    path: 'kownsl',
    loadChildren: () => import('./kownsl/kownsl.module')
      .then(m => m.KownslModule)
  },
  {
    path: 'zaken/:bronorganisatie/:identificatie',
    loadChildren: () => import('./zaak-detail/zaak-detail.module')
      .then(m => m.ZaakDetailModule)
  },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
