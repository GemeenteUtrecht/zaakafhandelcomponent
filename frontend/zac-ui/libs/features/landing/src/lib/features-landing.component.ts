import {Component, OnInit} from '@angular/core';
import {ZaakService} from '@gu/services';
import {Zaak} from '@gu/models';
import {LandingService} from './landing.service';
import {LandingPage} from '../models/landing-page';
import {SnackbarService} from '@gu/components';

/**
 * Landing page component.
 */
@Component({
  selector: 'gu-features-landing',
  templateUrl: './features-landing.component.html',
  styleUrls: ['./features-landing.component.scss']
})
export class FeaturesLandingComponent implements OnInit {
  readonly errorMessage = 'Er is een fout opgetreden bij het laden van landingspagina.'

  /** @type {boolean} Whether the landing page is loading. */
  isLoading: boolean = true;

  /** @type {(LandingPage|null)} The landing page once retrieved. */
  landingPage: LandingPage | null = null;

  /**
   * Constructor method.
   * @param {LandingService} landingService
   * @param {ZaakService} zaakService
   */
  constructor(private landingService: LandingService, private snackbarService: SnackbarService, private zaakService: ZaakService) {
  }

  //
  // Angular lifecycle.
  //

  ngOnInit() {
    this.getContextData();
  }

  //
  // Context.
  //

  getContextData() {
    this.landingService.landingPageRetrieve().subscribe(
      (landingPage) => this.landingPage = landingPage,
      (error) => this.reportError(error),
      () => this.isLoading = false,
    )
  }

  //
  // Events.
  //

  /**
   * Gets called when zaak (case) is selected.
   * @param {Zaak} zaak
   */
  onZaakSelectChange(zaak: Zaak) {
    this.zaakService.navigateToCase(zaak);
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    const message = error.error?.value ? error.error?.value[0] : this.errorMessage;
    this.snackbarService.openSnackBar(message, 'Sluiten', 'warn');
    this.isLoading = false;
    console.error(error);
  }
}
