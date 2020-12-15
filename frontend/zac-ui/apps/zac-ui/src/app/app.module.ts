import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { AppRoutingModule } from './app-routing.module';

import { SharedUiComponentsModule } from '@gu/components';

import { AppComponent } from './app.component';
import { HomeComponent } from './home/home.component';

import { KownslModule } from './kownsl/kownsl.module';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';

@NgModule({
  declarations: [
    AppComponent,
    HomeComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule,
    HttpClientXsrfModule.withOptions({
      cookieName: 'csrftoken',
      headerName: 'X-CSRFToken',
    }),
    KownslModule,
    SharedUiComponentsModule
  ],
  providers: [],
  bootstrap: [AppComponent],
})
export class AppModule {}
