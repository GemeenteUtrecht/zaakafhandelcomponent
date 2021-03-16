import { Component, OnInit } from '@angular/core';
import { menuItems, bottomMenuItems, MenuItem } from './constants/menu';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'zac-ui-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit {
  title = 'zac-ui';
  menuItems: MenuItem[] = menuItems;
  bottomMenuItems: MenuItem[] = bottomMenuItems;
  selectedMenu: string;

  constructor(
    private router: Router,
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
  }
}
