import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ZaakService } from '@gu/services';

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

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'];
    });
  }

  navigateToZaak(zaak: {bronorganisatie: string, identificatie: string}) {
    this.zaakService.navigateToCase(zaak);
  }
}
