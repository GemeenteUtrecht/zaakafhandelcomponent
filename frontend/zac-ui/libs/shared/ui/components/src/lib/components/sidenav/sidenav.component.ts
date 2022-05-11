import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MenuItem, User } from '@gu/models';

/**
 * <gu-sidenav [menuItems]="menuItems"
               [selectedParentMenu]="selectedMenu"
               [logoUrl]="logoUrl"
               [mobileLogoUrl]="mobileLogoUrl"
               [currentUser]="currentUser"
               (logOut)="logOutUser()">
 *
 * Side navigation bar for the application.
 */
@Component({
  selector: 'gu-sidenav',
  templateUrl: './sidenav.component.html',
  styleUrls: ['./sidenav.component.scss']
})
export class SidenavComponent {
  @Input() menuItems: MenuItem[];
  @Input() selectedParentMenu: string;
  @Input() logoUrl: string;
  @Input() mobileLogoUrl: string;
  @Input() currentUser: User;

  @Output() logOut = new EventEmitter<any>();

  expanded = false;

  constructor() { }

  /**
   * Toggle visibility of expanded navigation bar.
   */
  toggle() {
    this.expanded = false;
  }

  /**
   * Returns child route
   * @param route
   * @returns {string}
   */
  subtractParentRoute(route): string {
    return route.split('/')[1];
  }

  /**
   * Checks if user has staff rights.
   * @param adminOnly
   * @returns {boolean}
   */
  isAuthorised(adminOnly): boolean {
    return !adminOnly ? true : this.currentUser.isStaff;
  }

  /**
   * Logs user out.
   */
  logOutEvent(): void {
    this.logOut.emit();
  }
}
