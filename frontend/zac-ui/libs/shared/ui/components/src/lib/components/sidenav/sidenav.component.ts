import { Component, Input } from '@angular/core';
import { MenuItem, User } from '@gu/models';

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
  @Input() currentUser: User;

  expanded = false;

  constructor() { }

  toggle() {
    this.expanded = false;
  }

  subtractParentRoute(route) {
    return route.split('/')[1];
  }

  isAuthorised(adminOnly) {
    return !adminOnly ? true : this.currentUser.isStaff;
  }
}
