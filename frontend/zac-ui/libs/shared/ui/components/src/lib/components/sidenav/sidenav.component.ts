import {Component, EventEmitter, HostBinding, Input, Output} from '@angular/core';
import {MenuItem, User} from '@gu/models';

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
  @HostBinding('class') get class() {
    return this.expanded ? 'expanded' : '';
  }

  @Input() menuItems: MenuItem[];
  @Input() selectedParentMenu: string;
  @Input() logoUrl: string;
  @Input() mobileLogoUrl: string;
  @Input() currentUser: User;

  @Output() logOut = new EventEmitter<any>();

  expanded = this.getExpandedCache();

  //
  // Getters / setters.
  //

  /**
   * Gets the value for expanded from localStorage.
   */
  getExpandedCache(): boolean {
    try {
      return localStorage.getItem('sidenav.expanded') === 'true';
    } catch (e) {
      console.warn(e);
      return false;
    }
  }

  /**
   * Sets the value for expanded in localstorage.
   * @param {boolean} newValue
   */
  setExpandedCache(newValue: boolean) {
    try {
      return localStorage.setItem('sidenav.expanded', String(newValue));
    } catch (e) {
      console.warn(e);
    }
  }

  /**
   * Toggle navigation bar.
   */
  toggle() {
    const newValue = !this.expanded;
    this.expanded = newValue;
    this.setExpandedCache(newValue);
  }


  /**
   * Collapse expanded navigation bar.
   */
  onItemClick(e: Event) {
    e.stopPropagation();
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
