import { Component, Inject, Input, OnChanges, OnDestroy, OnInit, Renderer2, ViewChild } from '@angular/core';
import { DOCUMENT, Location } from '@angular/common';
import {Title} from '@angular/platform-browser';
import {ActivitiesService, UserService, ZaakService} from '@gu/services';
import {Observable} from 'rxjs';
import {Activity, User, Zaak} from '@gu/models';
import {ModalService, SnackbarService} from '@gu/components';
import {UntypedFormBuilder, UntypedFormControl, UntypedFormGroup} from '@angular/forms';
import {KownslSummaryComponent} from "./actions/adviseren-accorderen/kownsl-summary.component";
import {StatusComponent} from './actions/status/status.component';
import { ActivatedRoute, Router } from '@angular/router';
import {UserPermissionsComponent} from './overview/user-permissions/user-permissions.component';
import {BetrokkenenComponent} from './overview/betrokkenen/betrokkenen.component';
import {DocumentenComponent} from './documenten/documenten.component';
import { KetenProcessenComponent } from './actions/keten-processen/keten-processen.component';


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
export class FeaturesZaakDetailComponent implements OnInit, OnChanges, OnDestroy {
  /** @type {string} To identify the organisation. */
  @Input() bronorganisatie: string;

  /** @type {string} To identify the case (zaak). */
  @Input() identificatie: string;

  /** @type {string} To identify the activity). */
  @Input() activity: string;

  @ViewChild(KownslSummaryComponent) KownslSummaryComponent: KownslSummaryComponent;
  @ViewChild(StatusComponent) statusComponent: StatusComponent;
  @ViewChild(UserPermissionsComponent) UserPermissionsComponent: UserPermissionsComponent;
  @ViewChild(BetrokkenenComponent) betrokkenenComponent: BetrokkenenComponent;
  @ViewChild(DocumentenComponent) documentenComponent: DocumentenComponent;
  @ViewChild(KetenProcessenComponent) ketenProcessenComponent: KetenProcessenComponent;

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
  zaakAccessRequestForm: UntypedFormGroup;

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
   * @param {ActivitiesService} activitiesService
   * @param {FormBuilder} formBuilder
   * @param {ModalService} modalService
   * @param {SnackbarService} snackbarService
   * @param {Title} title
   * @param {UserService} userService
   * @param {ZaakService} zaakService
   * @param {Location} location
   * @param {ActivatedRoute} route
   * @param {Router} router
   * @param {Renderer2} renderer2
   * @param {Document} document
   */

  constructor(
    private activitiesService: ActivitiesService,
    private formBuilder: UntypedFormBuilder,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
    private title: Title,
    private userService: UserService,
    private zaakService: ZaakService,
    private location: Location,
    private route: ActivatedRoute,
    private router: Router,
    private renderer2: Renderer2,
    @Inject(DOCUMENT) private document: Document
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
  get commentControl(): UntypedFormControl {
    return this.zaakAccessRequestForm.get('comment') as UntypedFormControl;
  };


  /**
   * Whether user can force edit a closed case.
   * @returns {boolean}
   */
  get canForceEdit(): boolean {
    return !this.zaakData?.resultaat || this.zaakData?.kanGeforceerdBijwerken;
  }

  get showAccessRequest(): boolean {
    return this.canRequestAccess && !this.isAccessRequestSuccess && this.canForceEdit;
  }

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
   * A lifecycle hook that is called when any data-bound property of a directive changes. Define an ngOnChanges() method
   * to handle the changes.
   */
  ngOnChanges(): void {
    this.getContextData();

    localStorage.setItem('zaakidentificatie', this.bronorganisatie);
    localStorage.setItem('zaaknummer', this.identificatie);

    /*
     * /ui/zoeken route is now used for Oauth authorisation and can by configured via app.config.json: "redirectUri": "your_redirect_uri",
     * 'contezza-zac-doclib' script must by appended to complete Oauth login
     */
    if (this.router.url.includes('session_state')) {
      const script = this.renderer2.createElement('script');
      script.src = '/ui/assets/contezza-zac-doclib.js';
      this.renderer2.appendChild(this.document.body, script);
    }
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
   * Get the context.
   */
  getContextData(): void {
    this.canRequestAccess = false
    this.isLoading = true;

    this.fetchCaseDetails();
  }

  /**
   * Fetches the details of the case
   */
  fetchCaseDetails() {
    this.zaakService.retrieveCaseDetails(this.bronorganisatie, this.identificatie)
      .subscribe( res => {
        this.zaakData = res;
        this.mainZaakUrl = res.url ? res.url : null;
        this.zaakService.updateRecentlyViewedCase(res.url).subscribe();
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
    if (this.ketenProcessenComponent) {
      if (tab === 'acties') {
        this.ketenProcessenComponent.setIsVisible(true);
      } else {
        this.ketenProcessenComponent.setIsVisible(false);
      }
    }
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
   */
  ketenProcessenUpdate() {
    this.fetchCaseDetails();
    this.KownslSummaryComponent.update();
    this.statusComponent.update();
    this.betrokkenenComponent.update();
    this.documentenComponent.update();
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
