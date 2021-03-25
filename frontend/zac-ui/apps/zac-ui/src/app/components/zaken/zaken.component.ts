import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'gu-zaken',
  templateUrl: './zaken.component.html',
  styleUrls: ['./zaken.component.scss']
})

export class ZakenComponent implements OnInit {
  bronorganisatie: string;
  identificatie: string;

  constructor( private route: ActivatedRoute ) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'];
    });
  }

}
