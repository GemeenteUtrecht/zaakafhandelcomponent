import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { AppRoutingModule } from './app-routing.module';

import { SharedUiComponentsModule } from '@gu/ui-components';

import { AppComponent } from './app.component';
import { HomeComponent } from './home/home.component';

import { KownslModule } from './kownsl/kownsl.module';

@NgModule({
  declarations: [
    AppComponent,
    HomeComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    KownslModule,
    SharedUiComponentsModule
  ],
  providers: [],
  bootstrap: [AppComponent],
})
export class AppModule {}
