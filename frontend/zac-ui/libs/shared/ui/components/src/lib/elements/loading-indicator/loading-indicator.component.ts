import { Component, Input } from '@angular/core';

@Component({
  selector: 'gu-loading-indicator',
  templateUrl: './loading-indicator.component.html',
  styleUrls: ['./loading-indicator.component.scss']
})
export class LoadingIndicatorComponent {

  @Input() overlayGrey = false;
  @Input() hasContainer = false;
  @Input() loadingText: string;

  constructor() { }

}
