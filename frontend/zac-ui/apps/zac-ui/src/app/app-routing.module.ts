import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { HomeComponent } from './home/home.component';

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
  {
    path: 'zoeken',
    loadChildren: () => import('./search/search.module')
      .then(m => m.SearchModule)
  },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
