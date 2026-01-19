import { Component, OnInit } from '@angular/core';
import { PingService } from '@gu/services';

@Component({
  selector: 'app-warning-banner',
  templateUrl: './warning-banner.component.html',
  styleUrls: ['./warning-banner.component.scss']
})
export class WarningBannerComponent implements OnInit {
  warning: string | null = null;
  minimized: boolean = false;

  constructor(private healthcheckService: PingService) { }

  ngOnInit(): void {
    this.healthcheckService.pingServer().subscribe(data => {
      if (data.warning) {
        this.warning = data.warning;
      }
    });
  }

  toggleBanner(): void {
    this.minimized = !this.minimized;
  }
}