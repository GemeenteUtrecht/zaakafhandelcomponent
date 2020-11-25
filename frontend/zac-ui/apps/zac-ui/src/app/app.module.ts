import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppComponent } from './app.component';

import { SharedUiComponentsModule } from '@gu/ui-components';
import { FeaturesKownslModule } from '@gu/kownsl';

@NgModule({
  declarations: [AppComponent],
  imports: [
    BrowserModule,
    SharedUiComponentsModule,
    FeaturesKownslModule
  ],
  providers: [],
  bootstrap: [AppComponent],
})
export class AppModule {}
