import { Component, OnInit } from '@angular/core';
import { menuItems, bottomMenuItems, MenuItem } from './constants/menu';
import { NavigationEnd, Router } from '@angular/router';
import { filter, first } from 'rxjs/operators';
import { Observable } from 'rxjs';
import { User } from '@gu/models';
import { ApplicationHttpClient } from '@gu/services';

@Component({
  selector: 'zac-ui-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit {
  title = 'zac-ui';
  logoUrl = 'assets/gemeente-utrecht-logo.svg';
  mobileLogoUrl = 'assets/schild.png';
  currentUser: string;

  menuItems: MenuItem[] = menuItems;
  bottomMenuItems: MenuItem[] = bottomMenuItems;
  selectedMenu: string;

  constructor(
    private router: Router,
    private http: ApplicationHttpClient
  ) {
  }

  ngOnInit() {
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => {
        const parentRoute = event.url.split('/')[1].split('?')[0]
        this.selectedMenu = `${parentRoute}`;
        window.scrollTo(0, 0);
      });
    this.getCurrentUser()
      .pipe(first())
      .subscribe(res => {
        this.currentUser = `${res.firstName} ${res.lastName}`;
      });
  }

  getCurrentUser(): Observable<User> {
    const endpoint = encodeURI("/api/accounts/users/me");
    return this.http.Get<User>(endpoint);
  }
}
