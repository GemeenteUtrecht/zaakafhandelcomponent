import { BrowserModule } from '@angular/platform-browser';
import { NgModule, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { AppRoutingModule } from './app-routing.module';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';
import { registerLocaleData } from '@angular/common';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

import { LOCALE_ID } from '@angular/core';
import localeNL from '@angular/common/locales/nl';

import { SharedUiComponentsModule } from '@gu/components';

import { AppComponent } from './app.component';
import { HomeComponent } from './components/home/home.component';

import { KownslModule } from './components/kownsl/kownsl.module';
import { ZaakDetailModule } from './components/zaak-detail/zaak-detail.module';
import { WorkstackModule } from './components/workstack/workstack.module';

registerLocaleData(localeNL);

@NgModule({
  declarations: [
    AppComponent,
    HomeComponent,
  ],
  imports: [
    BrowserModule,
    BrowserAnimationsModule,
    AppRoutingModule,
    HttpClientModule,
    HttpClientXsrfModule.withOptions({
      cookieName: 'csrftoken',
      headerName: 'X-CSRFToken',
    }),
    SharedUiComponentsModule,
    KownslModule,
    ZaakDetailModule,
    WorkstackModule
  ],
  providers: [
    { provide: LOCALE_ID, useValue: "nl-NL" }
  ],
  bootstrap: [AppComponent],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class AppModule {}
