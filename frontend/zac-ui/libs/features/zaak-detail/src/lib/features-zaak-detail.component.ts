import {Component, Input, OnDestroy, OnInit, ViewChild} from '@angular/core';
import {Location} from '@angular/common';
import {Title} from '@angular/platform-browser';
import {ActivitiesService, UserService, ZaakService} from '@gu/services';
import {Observable} from 'rxjs';
import {Activity, User, Zaak} from '@gu/models';
import {ModalService, SnackbarService} from '@gu/components';
import {FormBuilder, FormControl, FormGroup} from '@angular/forms';
import {AdviserenAccorderenComponent} from "./actions/adviseren-accorderen/adviseren-accorderen.component";
import {StatusComponent} from './actions/status/status.component';
import {ActivatedRoute} from '@angular/router';
import {UserPermissionsComponent} from './overview/user-permissions/user-permissions.component';


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
export class FeaturesZaakDetailComponent implements OnInit, OnDestroy {
  /** @type {string} To identify the organisation. */
  @Input() bronorganisatie: string;

  /** @type {string} To identify the case (zaak). */
  @Input() identificatie: string;

  /** @type {string} To identify the activity). */
  @Input() activity: string;

  @ViewChild(AdviserenAccorderenComponent) adviserenAccorderenComponent: AdviserenAccorderenComponent;
  @ViewChild(StatusComponent) statusComponent: StatusComponent;
  @ViewChild(UserPermissionsComponent) UserPermissionsComponent: UserPermissionsComponent;

  /** @type {string} Message to show when access request is successfully submitted. */
  readonly accessRequestSuccessMessage: string = 'Je aanvraag is verstuurd.';


  /** @type {boolean} Whether this component is loading. */
  isLoading: boolean;

  /** @type {boolean} Whether an error occured. */
  showErrorBlock: boolean;

  /** @type {string} The error message. */
  errorMessage: string;

  /** @type {Activity[]} The activities for this case (zaak). */
  activityData: Activity[];

  /** @type {boolean} Whether the user is allowed to request access to this case (zaak). */
  canRequestAccess: boolean;

  /** @type {boolean} Whether an access request is being submitted. */
  isSubmittingAccessRequest: boolean;

  /** @type {boolean} Whether an access request is successfully submitted. */
  isAccessRequestSuccess: boolean;

  /** @type {string} Original title to restore on destroy. */
  originalTitle: string;

  /** @type {FormGroup} Form use to request acces to this case (zaak). */
  zaakAccessRequestForm: FormGroup;

  /** @type {User} The current logged in/hijacked user. */
  currentUser: User;

  /** @type {string} The case (zaak) url. */
  mainZaakUrl: string;

  /** @type {Zaak} The case (zaak). */
  zaakData: Zaak;

  /** Active tab */
  activeLink: string;

  /** Tabs */
  tabs: object[] = [
    {
      link: 'overzicht',
      title: 'Overzicht'
    },
    {
      link: 'acties',
      title: 'Acties'
    },
    {
      link: 'documenten',
      title: 'Documenten'
    },
    {
      link: 'objecten',
      title: 'Objecten'
    },
  ]

  /** Number of tasks */
  nTasks: number = null;

  /** Checklist availability */
  isChecklistAvailable = false;


  /**
   *
   * @param activitiesService
   * @param {FormBuilder} formBuilder
   * @param {ModalService} modalService
   * @param {SnackbarService} snackbarService
   * @param {Title} title
   * @param {UserService} userService
   * @param {ZaakService} zaakService
   * @param {Location} location
   * @param {ActivatedRoute} route
   */
  constructor(
    private activitiesService: ActivitiesService,
    private formBuilder: FormBuilder,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
    private title: Title,
    private userService: UserService,
    private zaakService: ZaakService,
    private location: Location,
    private route: ActivatedRoute,
  ) {
    this.zaakAccessRequestForm = this.formBuilder.group({
      comment: this.formBuilder.control(""),
    });

    this.route.params.subscribe(params => {
      this.activeLink = params['tabId'];
    });
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
    this.originalTitle = this.title.getTitle();
    this.title.setTitle(this.identificatie);
    this.fetchCurrentUser();
    this.getContextData();
  }

  /**
   * Cleanup just before Angular destroys the directive or component. Unsubscribe Observables and detach event handlers
   * to avoid memory leaks.
   */
  ngOnDestroy() {
    this.title.setTitle(this.originalTitle);
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
      .subscribe( res => {
        this.zaakData = res;
        this.mainZaakUrl = res.url ? res.url : null;
        this.fetchActivities(this.zaakData.url);
      }, err => {
        this.showErrorBlock = true;
        this.reportError(err.error);
      })
  }

  /**
   * Fetches the activities for this case (zaak).
   * @param {string} zaakUrl
   * @return {Observable}
   */
  fetchActivities(zaakUrl): void {
    this.activitiesService.getActivities(zaakUrl).subscribe( res => {
      this.activityData = res;
      if (this.activity) {
        setTimeout( () => {
          this.openModal('activities-modal')
        }, 1000)
      }
      this.isLoading = false;
    }, err => {
      this.isLoading = false;
    })
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

  getTabLink(tab) {
    return `/zaken/${this.bronorganisatie}/${this.identificatie}/${tab}`;
  }

  setUrl(tab) {
    this.location.go(this.getTabLink(tab))
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

  /**
   * Updates child components
   * @param event
   */
  ketenProcessenUpdate(event) {
    this.adviserenAccorderenComponent.update();
    this.statusComponent.update();
  }

  /**
   * Updates user permission component
   */
  permissionsUpdate() {
    this.UserPermissionsComponent.update();
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.isLoading = false;
    this.canRequestAccess = error.canRequestAccess;
    this.errorMessage = error.detail ?
      error.detail :
      error.reason ?
        error.reason :
        error.canRequestAccess ?
          "Je hebt geen toegang tot deze zaak" :
          "Er is een fout opgetreden";
    console.error(error);

    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
  }
}
