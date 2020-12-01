import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'gu-radio',
  templateUrl: './radio.component.html',
  styleUrls: ['./radio.component.scss']
})
export class RadioComponent implements OnInit {

  constructor() { }

  @Input() name: string;
  @Input() id: string;
  @Input() label: string;

  ngOnInit(): void {
  }

}
