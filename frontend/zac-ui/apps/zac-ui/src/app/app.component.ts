import { ChangeDetectorRef, Component, HostListener, OnInit } from '@angular/core';
import {NavigationEnd, Router} from '@angular/router';
import {filter} from 'rxjs/operators';
import {SnackbarService} from '@gu/components';
import { HealthService, UserService, ZaakService } from '@gu/services';
import {menuItems, MenuItem} from './constants/menu';
import { User } from '@gu/models';
import { DEFAULT_INTERRUPTSOURCES, Idle } from '@ng-idle/core';


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

  /** @type {string} Idle state. */
  idleState = "NOT_STARTED";

  userIsActive = true;

  /**
   * Constructor method.
   * @param {Idle} idle
   * @param {Router} router
   * @param {SnackbarService} snackbarService
   * @param {UserService} userService
   * @param {ZaakService} zaakService
   * @param {HealthService} healthService
   * @param {ChangeDetectorRef} cd
   */
  constructor (
    private idle: Idle,
    private router: Router,
    private snackbarService: SnackbarService,
    private userService: UserService,
    private zaakService: ZaakService,
    private healthService: HealthService,
    cd: ChangeDetectorRef
  ) {
    idle.setIdle(60); // how long can they be inactive before considered idle, in seconds (60 sec)
    idle.setInterrupts(DEFAULT_INTERRUPTSOURCES); // provide sources that will "interrupt" aka provide events indicating the user is active

    // When the user becomes idle
    idle.onIdleStart.subscribe(() => {
      this.idleState = "IDLE";
      console.log('inactive');
      this.userIsActive = false;
    });

    // When the user is no longer idle
    idle.onIdleEnd.subscribe(() => {
      this.idleState = "NOT_IDLE";
      cd.detectChanges();
      console.log('active');
      this.userIsActive = true;
      this.getHealth();
    });

  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.getHealth();
    this.reset();
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
   * check health of application
   */
  getHealth() {
    console.log('health check');
    this.healthService.getHealth().subscribe();

    // check health every 60s if the user is active
    setTimeout(() => {
      if (this.userIsActive) {
        this.getHealth();
      }
    }, 1000 * 60) // 60 seconds
  }

  /**
   * Call this method to start/reset the idle process
   */
  reset() {
    this.idle.watch();
    this.idleState = "NOT_IDLE";
  }

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
        this.router.navigate(['/']);
        window.location.reload();
      }, error => {
        this.reportError(error, this.logOutErrorMessage);
      }
    );
  }

  /**
   * Gets called when the hijack snackbar is dismissed.
   * Releases hijack.
   */
  hijackSnackBarDismissed(): void {
    this.userService.releaseHijack().subscribe(
      () => {
        this.getContextData();
        window.location.href = '/admin/accounts/user/';
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
