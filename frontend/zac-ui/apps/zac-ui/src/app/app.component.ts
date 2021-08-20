import {Component, OnInit} from '@angular/core';
import {NavigationEnd, Router} from '@angular/router';
import {filter} from 'rxjs/operators';
import {SnackbarService} from '@gu/components';
import {UserService, ZaakService} from '@gu/services';
import {menuItems, bottomMenuItems, MenuItem} from './constants/menu';


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
  /** @type {string} Possible error message to show. */
  readonly errorMessage: 'Er is een fout opgetreden bij het laden van de applicatie.'

  /** @type {string} The (relative) url to the logo. */
  logoUrl = 'assets/gemeente-utrecht-logo.svg';

  /** @type {string} The (relative) url to the mobile logo. */
  mobileLogoUrl = 'assets/schild.png';

  /** @type {string} The string representation of the current user. */
  currentUser: string;

  /** @type {MenuItem[]} The menu items to show in the center of the menu. */
  menuItems: MenuItem[] = menuItems;

  /** @type {MenuItem[]} The menu items to show in the bottom of the menu. */
  bottomMenuItems: MenuItem[] = bottomMenuItems;

  /** @type {string} Selected menu item. */
  selectedMenu: string;

  /**
   * Constructor method.
   * @param {Router} router
   * @param {SnackbarService} snackbarService
   * @param {UserService} userService
   * @param {ZaakService} zaakService
   */
  constructor(
    private router: Router,
    private snackbarService: SnackbarService,
    private userService: UserService,
    private zaakService: ZaakService,) {
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
        this.currentUser = this.userService.stringifyUser(user);

        if (isHijacked) {
          this.snackbarService.openSnackBar(`Je werkt nu namens ${this.currentUser}`, 'Stoppen', 'warn', 0)
            .afterDismissed()
            .subscribe(this.hijackSnackBarDismissed.bind(this));
        }
      });
  }

  //
  // Events
  //

  /**
   * Gets called when the hijack snackbar is dismissed.
   * Releases hijack.
   */
  hijackSnackBarDismissed(): void {
    this.userService.releaseHijack().subscribe(
      () => this.router.navigate([''])
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
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}
