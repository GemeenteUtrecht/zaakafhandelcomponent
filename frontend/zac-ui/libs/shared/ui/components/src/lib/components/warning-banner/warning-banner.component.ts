import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-warning-banner',
  templateUrl: './warning-banner.component.html',
  styleUrls: ['./warning-banner.component.css']
})
export class WarningBannerComponent {
  @Input() warningMessage: string | null = null;
}
