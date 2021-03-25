import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'gu-zaak-detail',
  templateUrl: './zaak-detail.component.html',
  styleUrls: ['./zaak-detail.component.scss']
})
export class ZaakDetailComponent implements OnInit {
  bronorganisatie: string;
  identificatie: string;

  isCollapsed = true;

  constructor( private route: ActivatedRoute ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'];
    });
  }

}
