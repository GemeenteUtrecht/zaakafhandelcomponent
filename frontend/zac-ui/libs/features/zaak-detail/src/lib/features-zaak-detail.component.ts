import { Component, OnInit } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute, Router } from '@angular/router';
import { Observable, of } from 'rxjs';
import { User, Zaak } from '@gu/models';
import { ModalService } from '@gu/components';
import { catchError, switchMap, tap } from 'rxjs/operators';
import { Activity } from '../models/activity';
import { FeaturesZaakDetailService } from './features-zaak-detail.service';

@Component({
  selector: 'gu-features-zaak-detail',
  templateUrl: './features-zaak-detail.component.html',
  styleUrls: ['./features-zaak-detail.component.scss']
})
export class FeaturesZaakDetailComponent implements OnInit {
  bronorganisatie: string;
  identificatie: string;
  mainZaakUrl: string;
  currentUser: User;

  zaakData: Zaak;
  activityData: Activity[];

  isLoading: boolean;
  hasError: boolean;
  errorMessage: string;

  loginUrl: string;

  activities = 2;

  constructor(
    private http: ApplicationHttpClient,
    private route: ActivatedRoute,
    private router: Router,
    private modalService: ModalService,
    private zaakDetailService: FeaturesZaakDetailService
  ) { }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'];

      this.fetchCurrentUser();
      this.fetchInformation();
    });
  }

  fetchInformation() {
    this.isLoading = true;
    this.zaakDetailService.getInformation(this.bronorganisatie, this.identificatie)
      .pipe(
        tap( res => {
          this.zaakData = res;
          this.mainZaakUrl = res.url ? res.url : null;
        }),
        catchError(res => {
          this.errorMessage = res.error.detail ? res.error.detail : 'Er is een fout opgetreden';
          this.hasError = true;
          this.isLoading = false;
          return of(null)
        }),
        switchMap(res => {
          const url = res?.url;
          return url ? this.fetchActivities(url) : of(null);
        })
      )
      .subscribe( activities => {
        this.activityData = activities;
        this.isLoading = false;
      }, error => {
        this.isLoading = false;
      })
  }

  fetchActivities(zaakUrl): Observable<Activity[]> {
    return this.zaakDetailService.getActivities(zaakUrl)
      .pipe(
        switchMap(res => {
          return of(res);
        }),
        catchError(() => {
          this.hasError = true;
          this.isLoading = false;
          return of(null);
        })
      )
  }

  fetchCurrentUser(): void {
    this.zaakDetailService.getCurrentUser().subscribe( res => {
      this.currentUser = res;
    })
  }

  openModal(id: string) {
    this.modalService.open(id);
  }

}
