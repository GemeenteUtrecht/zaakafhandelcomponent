import {BrowserModule, Title} from '@angular/platform-browser';
import { NgModule, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { AppRoutingModule } from './app-routing.module';
import { HTTP_INTERCEPTORS, HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';
import { registerLocaleData } from '@angular/common';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

import { LOCALE_ID } from '@angular/core';
import localeNL from '@angular/common/locales/nl';

import { AuthInterceptor } from './helpers/auth.interceptor';
import { LocaleInterceptor } from './helpers/locale.interceptor';
import { RetryInterceptor } from './helpers/retry.interceptor';

import { SharedUiComponentsModule } from '@gu/components';

import { AppComponent } from './app.component';

import { KownslModule } from './components/kownsl/kownsl.module';
import { ZakenModule } from './components/zaken/zaken.module';
import { WorkstackModule } from './components/workstack/workstack.module';
import { AuthProfilesModule } from './components/auth-profiles/auth-profiles.module';
import { DashboardModule } from './components/dashboard/dashboard.module';
import { NgIdleModule } from '@ng-idle/core';
import { LandingModule } from './components/landing/landing.module';


registerLocaleData(localeNL);

@NgModule({
  declarations: [
    AppComponent,
  ],
  imports: [
    AppRoutingModule,
    AuthProfilesModule,
    BrowserAnimationsModule,
    BrowserModule,
    DashboardModule,
    HttpClientModule,
    HttpClientXsrfModule.withOptions({
      cookieName: 'csrftoken',
      headerName: 'X-CSRFToken',
    }),
    KownslModule,
    LandingModule,
    NgIdleModule.forRoot(),
    SharedUiComponentsModule,
    WorkstackModule,
    ZakenModule,
  ],
  providers: [
    Title,
    { provide: HTTP_INTERCEPTORS, useClass: RetryInterceptor, multi: true },
    { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true },
    { provide: HTTP_INTERCEPTORS, useClass: LocaleInterceptor, multi: true },
    { provide: LOCALE_ID, useValue: "nl-NL" }
  ],
  bootstrap: [AppComponent],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class AppModule {}
