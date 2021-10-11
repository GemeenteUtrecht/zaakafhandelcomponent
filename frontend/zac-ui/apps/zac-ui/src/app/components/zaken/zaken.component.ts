import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ZaakService } from '@gu/services';

/**
 * Wrapper component containing "Zaak Select":
 *
 * <gu-zaak-select label='Direct naar zaak' placeholder='Zaaknummer' role='searchbox' (change)="navigateToZaak($event)"></gu-zaak-select>
 *
 * Allows the user to search on a zaak and redirect to it.
 */
@Component({
  selector: 'gu-zaken',
  templateUrl: './zaken.component.html',
  styleUrls: ['./zaken.component.scss']
})

export class ZakenComponent implements OnInit {
  bronorganisatie: string;
  identificatie: string;

  constructor(
    private route: ActivatedRoute,
    private zaakService: ZaakService) {}

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
      this.identificatie = params['identificatie'];
    });
  }

  //
  // Events.
  //

  /**
   * Navigates to selected zaak.
   * @param {{bronorganisatie: string, identificatie: string}} zaak
   */
  navigateToZaak(zaak: {bronorganisatie: string, identificatie: string}) {
    this.zaakService.navigateToCase(zaak);
  }
}
