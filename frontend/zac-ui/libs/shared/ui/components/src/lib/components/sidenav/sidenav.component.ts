import { Component, Input } from '@angular/core';
import { MenuItem } from '@gu/models';

@Component({
  selector: 'gu-sidenav',
  templateUrl: './sidenav.component.html',
  styleUrls: ['./sidenav.component.scss']
})
export class SidenavComponent {
  @Input() menuItems: MenuItem[];
  @Input() bottomMenuItems: MenuItem[];
  @Input() selectedParentMenu: string;
  @Input() logoUrl: string;
  @Input() mobileLogoUrl: string;
  @Input() currentUser: string;
  @Input() searchComponentName: string;

  expanded = false;

  constructor() { }

  toggle() {
    this.expanded = false;
  }

  subtractParentRoute(route) {
    return route.split('/')[1];
  }
}
