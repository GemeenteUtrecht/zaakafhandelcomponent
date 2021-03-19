import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { HomeComponent } from './components/home/home.component';
import { ZaakDetailModule } from './components/zaak-detail/zaak-detail.module';

const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    component: HomeComponent,
  },
  {
    path: 'kownsl',
    loadChildren: () => import('./components/kownsl/kownsl.module')
      .then(m => m.KownslModule)
  },
  {
    path: 'zaken',
    loadChildren: () => import('./components/zaak-detail/zaak-detail.module')
      .then(m => m.ZaakDetailModule)
  },
  {
    path: 'zoeken',
    loadChildren: () => import('./components/search/search.module')
      .then(m => m.SearchModule)
  },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
