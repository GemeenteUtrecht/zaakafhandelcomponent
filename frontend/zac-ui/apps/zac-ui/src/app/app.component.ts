import { Component, HostListener, OnInit } from '@angular/core';
import {NavigationEnd, Router} from '@angular/router';
import {filter} from 'rxjs/operators';
import {SnackbarService} from '@gu/components';
import {UserService, ZaakService} from '@gu/services';
import {menuItems, MenuItem} from './constants/menu';
import { User } from '@gu/models';


/**
 * <gu-zac-ui-root></gu-zac-ui-root>
 *
 * Application root.
 */
@Component({
  selector: 'gu-zac-ui-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit {
  /** @type {string} Possible error messages to show. */
  readonly errorMessage: 'Er is een fout opgetreden bij het laden van de applicatie.'
  readonly logOutErrorMessage: 'Uitloggen mislukt.'

  /** @type {string} The (relative) url to the logo. */
  logoUrl = 'assets/images/gemeente-utrecht-logo.svg';

  /** @type {string} The (relative) url to the mobile logo. */
  mobileLogoUrl = 'assets/images/schild.png';

  /** @type {string} The string representation of the current user. */
  currentUser: User;

  /** @type {MenuItem[]} The menu items to show in the center of the menu. */
  menuItems: MenuItem[] = menuItems;

  /** @type {string} Selected menu item. */
  selectedMenu: string;

  /** @type {number} Time out handler. */
  timeoutId: number;

  /** @type {number} Maximum time for inactive user. */
  maxUserInactivityTime: number = 30 * 60 * 1000; // 30 minutes

  /**
   * Constructor method.
   * @param {Router} router
   * @param {SnackbarService} snackbarService
   * @param {UserService} userService
   * @param {ZaakService} zaakService
   */
  constructor (
    private router: Router,
    private snackbarService: SnackbarService,
    private userService: UserService,
    private zaakService: ZaakService,
  ) {
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => {
        const parentRoute = event.url.split('/')[1].split('?')[0];
        this.selectedMenu = `${parentRoute}`;
        window.scrollTo(0, 0);
      });

    this.getContextData();
    this.checkTimeOut();
  }

  //
  // Context.
  //

  /**
   * Retrieves the current user.
   */
  getContextData(): void {
    this.userService.getCurrentUser()
      .subscribe(([user, isHijacked]) => {
        this.currentUser = user;

        if (isHijacked) {
          this.snackbarService.openSnackBar(`Je werkt nu namens ${this.userService.stringifyUser(this.currentUser)}`, 'Stoppen', 'accent', 0)
            .afterDismissed()
            .subscribe((matSnackBarDismiss) => {
              if(matSnackBarDismiss.dismissedByAction) {
                this.hijackSnackBarDismissed()
              }
            });
        }
      });
  }

  //
  // Events
  //

  /**
   * Call API to log out user.
   */
  logOutUser() {
    this.userService.logOutUser().subscribe(
      () => {
        this.router.navigate([''])
      }, error => {
        this.reportError(error, this.logOutErrorMessage);
      }
    );
  }

  /**
   * Clear time out if user shows activity.
   */
  @HostListener('window:keydown')
  @HostListener('window:mousedown')
  @HostListener('window:mousemove')
  checkUserActivity() {
    clearTimeout(this.timeoutId);
    this.checkTimeOut();
  }

  /**
   * Log user out after timeout.
   */
  checkTimeOut() {
    this.timeoutId = setTimeout(() => {
      this.logOutUser()
    }, this.maxUserInactivityTime);
  }

  /**
   * Gets called when the hijack snackbar is dismissed.
   * Releases hijack.
   */
  hijackSnackBarDismissed(): void {
    this.userService.releaseHijack().subscribe(
      () => {
        this.getContextData();
        this.router.navigate([''])
      }
    );
  }

  /**
   * Gets called when a Zaak (case) is selected.
   * Navigates to the case's detail view.
   * @param {Zaak} zaak
   */
  zaakSelected(zaak: { bronorganisatie: string, identificatie: string }): void {
    this.zaakService.navigateToCase(zaak);
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   * @param {string} message
   */
  reportError(error: any, message: string): void {
    this.snackbarService.openSnackBar(message, 'Sluiten', 'warn');
    console.error(error);
  }
}
