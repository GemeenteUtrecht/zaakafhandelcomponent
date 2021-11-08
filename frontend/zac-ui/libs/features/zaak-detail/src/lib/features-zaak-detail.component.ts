import {Component, Input, OnInit, ViewChild} from '@angular/core';
import {ActivitiesService, UserService, ZaakService} from '@gu/services';
import {Observable, of} from 'rxjs';
import {Activity, User, Zaak} from '@gu/models';
import {ModalService, SnackbarService} from '@gu/components';
import {catchError, switchMap, tap} from 'rxjs/operators';
import {FormBuilder, FormControl, FormGroup} from '@angular/forms';
import {AdviserenAccorderenComponent} from "./adviseren-accorderen/adviseren-accorderen.component";
import { StatusComponent } from './status/status.component';


/**
 * <gu-features-zaak-detail [bronorganisatie]="bronorganisatie" [identificatie]="identificatie"></gu-features-zaak-detail>
 *
 * Case (zaak) detail view component.
 *
 * Requires bronorganisatie: string input to identify the organisation.
 * Requires identificatie: string input to identify the case (zaak).
 */
@Component({
  selector: 'gu-features-zaak-detail',
  templateUrl: './features-zaak-detail.component.html',
  styleUrls: ['./features-zaak-detail.component.scss']
})
export class FeaturesZaakDetailComponent implements OnInit {
  /** @type {string} To identify the organisation. */
  @Input() bronorganisatie: string;

  /** @type {string} To identify the case (zaak). */
  @Input() identificatie: string;

  /** @type {string} To identify the activity). */
  @Input() activity: string;

  @ViewChild(AdviserenAccorderenComponent) adviserenAccorderenComponent: AdviserenAccorderenComponent;
  @ViewChild(StatusComponent) statusComponent: StatusComponent;

  /** @type {string} Message to show when access request is successfully submitted. */
  readonly accessRequestSuccessMessage: string = 'Je aanvraag is verstuurd.';


  /** @type {boolean} Whether this component is loading. */
  isLoading: boolean;

  /** @type {boolean} Whether an error occured. */
  hasError: boolean;

  /** @type {string} The error message. */
  errorMessage: string;

  /** @type {Activity[]} The activities for this case (zaak). */
  activityData: Activity[];

  /** @type {Activity[]} The active activities for this case (zaak). */
  activeActivities: Activity[];

  /** @type {boolean} Whether the user is allowed to request access to this case (zaak). */
  canRequestAccess: boolean;

  /** @type {boolean} Whether an access request is being submitted. */
  isSubmittingAccessRequest: boolean;

  /** @type {boolean} Whether an access request is successfully submitted. */
  isAccessRequestSuccess: boolean;

  /** @type {FormGroup} Form use to request acces to this case (zaak). */
  zaakAccessRequestForm: FormGroup;

  /** @type {User} The current logged in/hijacked user. */
  currentUser: User;

  /** @type {string} The case (zaak) url. */
  mainZaakUrl: string;

  /** @type {Zaak} The case (zaak). */
  zaakData: Zaak;


  /**
   *
   * @param activitiesService
   * @param {FormBuilder} formBuilder
   * @param {ModalService} modalService
   * @param {SnackbarService} snackbarService
   * @param {UserService} userService
   * @param {ZaakService} zaakService
   */
  constructor(
    private activitiesService: ActivitiesService,
    private formBuilder: FormBuilder,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
    private userService: UserService,
    private zaakService: ZaakService,
  ) {
    this.zaakAccessRequestForm = this.formBuilder.group({
      comment: this.formBuilder.control(""),
    })
  }

  //
  // Getters / setters.
  //

  /**
   * Returns the comment FormControl.
   * @return {FormControl}
   */
  get commentControl(): FormControl {
    return this.zaakAccessRequestForm.get('comment') as FormControl;
  };

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.fetchCurrentUser();
    this.getContextData();
  }

  //
  // Context.
  //

  /**
   * Fetches the details of the case (zaak).
   */
  getContextData(): void {
    this.canRequestAccess = false
    this.isLoading = true;

    this.zaakService.retrieveCaseDetails(this.bronorganisatie, this.identificatie)
      .pipe(
        tap(res => {
          this.zaakData = res;
          this.mainZaakUrl = res.url ? res.url : null;
        }),
        catchError((res) => {
          this.reportError(res.error)
          return of(null)
        }),
        switchMap(res => {
          const url = res?.url;
          return url ? this.fetchActivities(url) : of(null);
        })
      )
      .subscribe({
        next: (activities) => {
          if (!activities) {
            return;
          }
          this.activityData = activities;
          this.activeActivities = activities.filter(activity => {
            return activity.status === 'on_going'
          })
        },
        error: (error) => this.reportError(error.error),
        complete: () => this.isLoading = false
      })
  }

  /**
   * Fetches the activities for this case (zaak).
   * @param {string} zaakUrl
   * @return {Observable}
   */
  fetchActivities(zaakUrl): Observable<Activity[]> {
    return this.activitiesService.getActivities(zaakUrl)
      .pipe(
        switchMap(res => {
          if (this.activity) {
            setTimeout( () => {
              this.openModal('activities-modal')
            }, 1000)
          }
          return of(res);
        }),
        catchError(this.reportError.bind(this))
      )
  }

  /**
   * Fetches the current user.
   */
  fetchCurrentUser(): void {
    this.userService.getCurrentUser().subscribe(([user,]) => {
      this.currentUser = user;
    })
  }

  /**
   * Opens a modal.
   * @param {string} id The id of the modal to open.
   */
  openModal(id: string): void {
    this.modalService.open(id);
  }

  //
  // Events.
  //

  /**
   * Gets called when the access request is submitted.
   */
  onSubmitAccessRequest(): void {
    this.isSubmittingAccessRequest = true;

    const comment = this.commentControl.value ? this.commentControl.value : undefined;
    const formData = {
      zaak: {
        bronorganisatie: this.bronorganisatie,
        identificatie: this.identificatie
      },
      comment: comment
    }

    this.zaakService.createAccessRequest(formData).subscribe(() => {
      this.isSubmittingAccessRequest = false;
      this.isAccessRequestSuccess = true;
    }, this.reportError.bind(this))
  }

  ketenProcessenUpdate(event) {
    this.adviserenAccorderenComponent.update();
    this.statusComponent.update();
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.canRequestAccess = error.canRequestAccess;
    this.errorMessage = error.detail ?
      error.detail :
      error.reason ?
        error.reason :
        error.canRequestAccess ?
          "Je hebt geen toegang tot deze zaak" :
          "Er is een fout opgetreden";

    console.error(error);
    this.hasError = true;
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
  }
}
