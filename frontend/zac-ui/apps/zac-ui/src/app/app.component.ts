import {Component, OnInit} from '@angular/core';
import {menuItems, bottomMenuItems, MenuItem} from './constants/menu';
import {NavigationEnd, Router} from '@angular/router';
import {filter} from 'rxjs/operators';
import {ApplicationHttpClient, UserService, ZaakService} from '@gu/services';
import {SnackbarService} from "@gu/components";

@Component({
  selector: 'gu-zac-ui-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit {
  readonly errorMessage: 'Er is een fout opgetreden bij het laden van de applicatie.'

  title = 'zac-ui';
  logoUrl = 'assets/gemeente-utrecht-logo.svg';
  mobileLogoUrl = 'assets/schild.png';
  currentUser: string;

  menuItems: MenuItem[] = menuItems;
  bottomMenuItems: MenuItem[] = bottomMenuItems;
  selectedMenu: string;

  constructor(
    private http: ApplicationHttpClient,
    private router: Router,
    private snackbarService: SnackbarService,
    private userService: UserService,
    private zaakService: ZaakService,) {
  }

  ngOnInit() {
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => {
        const parentRoute = event.url.split('/')[1].split('?')[0];
        this.selectedMenu = `${parentRoute}`;
        window.scrollTo(0, 0);
      });

    this.userService.getCurrentUser()
      .subscribe(([user, isHijacked]) => {
        this.currentUser = this.userService.stringifyUser(user);

        if (isHijacked) {
          this.snackbarService.openSnackBar(`Je werkt nu namens ${this.currentUser}`, 'Stoppen', 'warn', 0)
            .afterDismissed()
            .subscribe(this.releaseHijack.bind(this));
        }
      });
  }

  navigateToZaak(zaak: { bronorganisatie: string, identificatie: string }) {
    this.zaakService.navigateToCase(zaak);
  }

  //
  // Events
  //

  releaseHijack() {
    this.userService.releaseHijack().subscribe(
      () => this.router.navigate([''])
    );
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
