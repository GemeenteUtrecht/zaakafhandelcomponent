import {Component, OnInit} from '@angular/core';
import {ActivatedRoute} from '@angular/router';

/**
 * const routes: Routes = [
 *   {
 *     path: ':bronorganisatie/:identificatie',
 *     component: ZaakDetailComponent
 *   }
 * ];
 *
 * Case (zaak) detail view.
 *
 * Requires bronorganisatie: string param to identify the organisation.
 * Requires identificatie: string param to identify the case (zaak).
 */
@Component({
  selector: 'gu-zaak-detail',
  templateUrl: './zaak-detail.component.html',
})
export class ZaakDetailComponent implements OnInit {
  /** @type {string} To identify the organisation. */
  bronorganisatie: string;

  /** @type {string} To identify the case (zaak). */
  identificatie: string;

  /** @type {string} To identify the activity). */
  activity: string;

  /**
   * Constructor method.
   * @param {ActivatedRoute} route
   */
  constructor(private route: ActivatedRoute) {
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'].split('?')[0];
    });

    this.route.queryParams.subscribe(params => {
      const activityParam = params['activities'];
      if (activityParam) {
        this.activity = activityParam;
      }
    });
  }

}
