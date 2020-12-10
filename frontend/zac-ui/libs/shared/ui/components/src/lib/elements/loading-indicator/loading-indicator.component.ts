import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'gu-loading-indicator',
  templateUrl: './loading-indicator.component.html',
  styleUrls: ['./loading-indicator.component.scss']
})
export class LoadingIndicatorComponent implements OnInit {

  @Input() overlayGrey = false;
  @Input() hasContainer = false;

  constructor() { }

  ngOnInit(): void {
  }

}
