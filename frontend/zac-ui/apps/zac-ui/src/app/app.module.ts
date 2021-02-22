import { BrowserModule } from '@angular/platform-browser';
import { NgModule, CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { AppRoutingModule } from './app-routing.module';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';
import { registerLocaleData } from '@angular/common';

import { LOCALE_ID } from '@angular/core';
import localeNL from '@angular/common/locales/nl';

import { SharedUiComponentsModule } from '@gu/components';

import { AppComponent } from './app.component';
import { HomeComponent } from './home/home.component';

import { KownslModule } from './kownsl/kownsl.module';
import { ZaakDetailModule } from './zaak-detail/zaak-detail.module';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

registerLocaleData(localeNL);

@NgModule({
  declarations: [
    AppComponent,
    HomeComponent
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
  ],
  providers: [
    { provide: LOCALE_ID, useValue: "nl-NL" }
  ],
  bootstrap: [AppComponent],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class AppModule {}
