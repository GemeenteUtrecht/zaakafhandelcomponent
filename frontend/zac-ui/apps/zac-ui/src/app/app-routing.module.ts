import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

const routes: Routes = [
  {
    path: '',
    loadChildren: () =>
      import('./components/landing/landing.module').then((m) => m.LandingModule),
  },
  {
    path: 'kownsl',
    loadChildren: () =>
      import('./components/kownsl/kownsl.module').then((m) => m.KownslModule),
  },
  {
    path: 'werkvoorraad',
    loadChildren: () =>
      import('./components/workstack/workstack.module').then((m) => m.WorkstackModule),
  },
  {
    path: 'zaken',
    loadChildren: () =>
      import('./components/zaken/zaken.module').then((m) => m.ZakenModule),
  },
  {
    path: 'zoeken',
    loadChildren: () =>
      import('./components/search/search.module').then((m) => m.SearchModule),
  },
  {
    path: 'zaak-starten',
    loadChildren: () =>
      import('./components/start-case/start-case.module').then((m) => m.StartCaseModule),
  },
  {
    path: 'rapportages',
    loadChildren: () =>
      import('./components/reports/reports.module').then((m) => m.ReportsModule),
  },
  {
    path: 'autorisaties',
    loadChildren: () =>
      import('./components/auth-profiles/auth-profiles.module').then((m) => m.AuthProfilesModule),
  },
  {
    path: 'dashboard',
    loadChildren: () =>
      import('./components/dashboard/dashboard.module').then((m) => m.DashboardModule),
  },
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { relativeLinkResolution: 'legacy' })],
  exports: [RouterModule],
})
export class AppRoutingModule {}
