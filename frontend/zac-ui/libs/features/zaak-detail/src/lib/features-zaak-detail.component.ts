import { Component, OnInit } from '@angular/core';
import {ApplicationHttpClient, ZaakService} from '@gu/services';
import { ActivatedRoute, Router } from '@angular/router';
import { Observable, of } from 'rxjs';
import { User, Zaak } from '@gu/models';
import { ModalService } from '@gu/components';
import { catchError, switchMap, tap } from 'rxjs/operators';
import { Activity } from '../models/activity';
import { FeaturesZaakDetailService } from './features-zaak-detail.service';
import { FormBuilder, FormControl, FormGroup } from '@angular/forms';

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
  zaakAccessRequestForm: FormGroup;

  isLoading: boolean;
  hasError: boolean;
  errorMessage: string;

  canRequestAccess: boolean;
  isSubmittingAccessRequest: boolean;
  accessRequestSuccess: boolean;
  accessRequestSuccessMessage: string = 'Je aanvraag is verstuurd.';
  accessRequestFinished: boolean;

  loginUrl: string;

  activityData: Activity[];
  activeActivities: Activity[];

  constructor(
    private fb: FormBuilder,
    private http: ApplicationHttpClient,
    private route: ActivatedRoute,
    private router: Router,
    private modalService: ModalService,
    private zaakDetailService: FeaturesZaakDetailService,
    private zaakService: ZaakService,
  ) {
    this.zaakAccessRequestForm = this.fb.group({
      comment: this.fb.control(""),
    })
  }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'];

      this.fetchCurrentUser();
      this.fetchInformation();
    });
  }

  fetchInformation() {
    this.canRequestAccess = false
    this.isLoading = true;
    this.zaakService.retrieveCaseDetails(this.bronorganisatie, this.identificatie)
      .pipe(
        tap( res => {
          this.zaakData = res;
          this.mainZaakUrl = res.url ? res.url : null;
        }),
        catchError(res => {
          this.canRequestAccess = res.error.canRequestAccess;
          this.errorMessage = res.error.detail ?
            res.error.detail :
            res.error.reason ?
              res.error.reason :
                res.error.canRequestAccess ?
                  "Je hebt geen toegang tot deze zaak" :
                  "Er is een fout opgetreden";
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
        if (activities) {
          this.activityData = activities;
          this.activeActivities = activities.filter(activity => {
            return activity.status === 'on_going'
          })
        }
        this.isLoading = false;
      }, error => {
        this.isLoading = false;
      })
  }

  fetchActivities(zaakUrl): Observable<Activity[]> {
    return this.zaakDetailService.getActivities(zaakUrl)
      .pipe(
        switchMap(res => {
          this.openActivitiesModal();
          return of(res);
        }),
        catchError(() => {
          this.hasError = true;
          this.isLoading = false;
          return of(null);
        })
      )
  }

  openActivitiesModal() {
    this.route.queryParams.subscribe(params => {
      const activityParam = params['activities'];
      if (activityParam) {
        this.openModal('activities-modal')
      }
    });
  }

  fetchCurrentUser(): void {
    this.zaakDetailService.getCurrentUser().subscribe( res => {
      this.currentUser = res;
    })
  }

  openModal(id: string) {
    this.modalService.open(id);
  }

  get commentControl(): FormControl {
    return this.zaakAccessRequestForm.get('comment') as FormControl;
  };

  submitAccessRequest() {
    this.isSubmittingAccessRequest = true;
    const comment = this.commentControl.value ? this.commentControl.value : undefined;
    const formData = {
      zaak: {
        bronorganisatie: this.bronorganisatie,
        identificatie: this.identificatie
      },
      comment: comment
    }
    this.zaakDetailService.postAccessRequest(formData).subscribe(() => {
      this.isSubmittingAccessRequest = false;
      this.accessRequestFinished = true;
      this.accessRequestSuccess = true;
    }, error => {
      this.isSubmittingAccessRequest = false;
      this.accessRequestFinished = true;
      this.accessRequestSuccess = false;
      this.errorMessage = error.detail ? error.detail : "De aanvraag is niet gelukt"
    })
  }

}
