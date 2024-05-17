import { Component, Input, OnInit } from '@angular/core';
import { ActiviteitenService } from './activiteiten.service';
import {
  Activity,
  Document,
  ReadWriteDocument,
  ShortDocument,
  User,
  UserGroupDetail,
  UserSearchResult, Zaak
} from '@gu/models';
import { UntypedFormArray, UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import { SnackbarService } from '@gu/components';
import {UserService} from '@gu/services';

/**
 * This component allows the user to set and edit activities.
 *
 * Requires zaak: object with the case data.
 * Requires currentUser: User input to identify the current user.
 * Requires activityData: All activity data.
 */
@Component({
  selector: 'gu-activiteiten',
  templateUrl: './activiteiten.component.html',
  styleUrls: ['./activiteiten.component.scss']
})
export class ActiviteitenComponent implements OnInit {
  @Input() zaak: Zaak;
  @Input() currentUser: User;
  @Input() activityData: Activity[];

  activityForm: UntypedFormGroup;
  addActivityForm: UntypedFormGroup;
  assignUserForm: UntypedFormGroup;

  users: UserSearchResult[] = [];
  userGroups: UserGroupDetail[] = [];

  ongoingData: Activity[] = [];
  finishedData: Activity[] = [];

  isLoading: boolean;
  errorMessage: string;
  openNoteEditField: number;
  openAssigneeEditField: number;
  openDocumentUploadForm: number;

  expandedActivity: Activity|null;

  showAddActivityButton: boolean;
  showCloseActivityConfirmation: number;
  showDeleteActivityConfirmation: number;

  isSubmitting: boolean;

  activityDocs: ShortDocument[] = [];
  ongoingActivityDocs: ShortDocument[] = [];
  finishedActivityDocs: ShortDocument[] = [];
  isFetchingDocuments: boolean;

  constructor(private actvititeitenService: ActiviteitenService, private fb: UntypedFormBuilder, private snackbarService: SnackbarService, private userService: UserService) { }

  //
  // Getters / setters.
  //

  get addActivityName(): UntypedFormControl {
    return this.addActivityForm.get('name') as UntypedFormControl;
  };

  get addActivityRemarks(): UntypedFormControl {
    return this.addActivityForm.get('remarks') as UntypedFormControl;
  };

  get notesControl(): UntypedFormArray {
    return this.activityForm.get('notes') as UntypedFormArray;
  };

  get assignUserControl(): UntypedFormArray {
    return this.assignUserForm.get('user') as UntypedFormArray;
  };

  get assignUserGroupControl(): UntypedFormArray {
    return this.assignUserForm.get('group') as UntypedFormArray;
  };

  get canForceEdit(): boolean {
    return !this.zaak.resultaat || this.zaak.kanGeforceerdBijwerken;
  }

  /**
   * Returns the stringied activity.createdBy value.
   * @param {Object} obj
   * @return {string}
   */
  getCreatedBy(obj: {[index: string]: any, createdBy: User }) {
    const user = obj.createdBy;
    return this.userService.stringifyUser(user);
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.createForm();
  }

  //
  // Context.
  //

  /**
   * Initiate controls for the Reactive form
   */
  createForm() {
    this.activityForm = this.fb.group({
      notes: this.fb.array(this.addNotesControl(this.activityData))
    })

    this.assignUserForm = this.fb.group({
      user: this.fb.array(this.addAssignUserControl(this.activityData)),
      group: this.fb.array(this.addAssignUserGroupControl(this.activityData))
    })

    this.addActivityForm = this.fb.group({
      name: this.fb.control("", Validators.required),
      remarks: this.fb.control(""),
    })

    this.isLoading = true;
    this.formatActivityData(this.activityData);
    this.fetchDocuments(this.activityData);
    this.isLoading = false;
  }

  /**
   * Add control for each existing activity.
   * @param data
   * @returns {any}
   */
  addNotesControl(data) {
    return data.map( () => this.fb.control("", Validators.required) )
  }

  /**
   * Add control for each existing activity.
   * @param data
   * @returns {any}
   */
  addAssignUserControl(data) {
    return data.map( () => this.fb.control("", Validators.required) )
  }

  /**
   * Add control for each existing activity.
   * @param data
   * @returns {any}
   */
  addAssignUserGroupControl(data) {
    return data.map( () => this.fb.control("", Validators.required) )
  }

  /**
   * Returns control for the given index.
   * @param {number} index
   * @returns {FormControl}
   */
  notes(index: number): UntypedFormControl {
    return this.notesControl.at(index) as UntypedFormControl;
  }

  /**
   * Returns control for the given index.
   * @param {number} index
   * @returns {FormControl}
   */
  assignedUserControlIndex(index: number): UntypedFormControl {
    return this.assignUserControl.at(index) as UntypedFormControl;
  }

  /**
   * Returns control for the given index.
   * @param {number} index
   * @returns {FormControl}
   */
  assignedUserGroupControlIndex(index: number): UntypedFormControl {
    return this.assignUserGroupControl.at(index) as UntypedFormControl;
  }

  /**
   * Find accounts on search input.
   * @param searchInput
   */
  onSearchAccounts(searchInput) {
    if (searchInput) {
      this.actvititeitenService.getAccounts(searchInput).subscribe(res => {
        this.users = res.results;
      }, error => {
        console.error(error);
        this.reportError(error)
      });
    }
  }


  /**
   * Find user groups on search input.
   * @param searchInput
   */
  onSearchUserGroups(searchInput) {
    this.actvititeitenService.getUserGroups(searchInput).subscribe(res => {
      this.userGroups = res.results;
    }, error => {
      console.error(error);
      this.reportError(error)
    });
  }

  /**
   * Fetch all activities.
   */
  fetchActivities() {
    if (this.zaak.url) {
      this.actvititeitenService.getActivities(this.zaak.url)
        .subscribe(res => {
          this.activityData = res;
          this.createForm();
        }, error => {
          console.error(error);
          this.reportError(error)
        });
    }
  }

  /**
   * Fetch documents for all activities.
   * @param activities
   */
  fetchDocuments(activities) {
    this.isFetchingDocuments = true;
    this.actvititeitenService.getDocuments(activities).subscribe( res => {
      this.activityDocs = res;
      this.formatDocsData(this.activityDocs);
      this.isFetchingDocuments = false;
    }, error => {
      console.log(error);
      this.isFetchingDocuments = false;
    });
  }

  /**
   * Separate ongoing and finished activities.
   * @param {Activity[]} activities
   */
  formatActivityData(activities: Activity[]) {
    this.ongoingData = activities.filter(activity => {
      return activity.status === 'on_going'
    })
    this.finishedData = activities.filter(activity => {
      return activity.status === 'finished'
    })
  }

  /**
   * Separate ongoing and finished activity documents.
   * @param {ShortDocument[]} activityDocs
   */
  formatDocsData(activityDocs: ShortDocument[]) {
    this.ongoingActivityDocs = activityDocs.filter((activity, i) => {
      return this.activityData[i].status === 'on_going';
    })
    this.finishedActivityDocs = activityDocs.filter((activity, i) => {
      return this.activityData[i].status === 'on_going';
    })
  }

  /**
   * Create new activity.
   */
  createNewActivity() {
    this.isSubmitting = true;
    const formData = {
      zaak: this.zaak.url,
      name: this.addActivityName.value,
      remarks: this.addActivityRemarks.value
    }

    this.actvititeitenService.postNewActivity(formData).subscribe(() => {
      this.isSubmitting = false;
      this.addActivityForm.reset();
      this.showAddActivityButton = false
      this.fetchActivities();
    }, res =>  {
      this.isSubmitting = false;
      this.addActivityForm.reset();
      this.reportError(res)
    })
  }

  /**
   * Create note for activity.
   * @param activityId
   * @param index
   */
  submitNotes(activityId, index) {
    this.isLoading = true
    const formData = {
      activity: activityId,
      notes: this.notes(index).value
    }

    this.actvititeitenService.postNotes(formData).subscribe(() => {
      this.activityForm.reset();
      this.openNoteEditField = null;
      this.fetchActivities();
    }, res =>  {
      this.reportError(res)
    })
  }

  /**
   * Assign an activity to a user or user group.
   * @param activityId
   * @param index
   * @param {"user" | "userGroup"} assignType
   */
  submitAssign(activityId, index, assignType: 'user' | 'userGroup') {
    this.isLoading = true
    let formData = {};
    switch (assignType) {
      case 'user':
        formData = {
          userAssignee: this.assignedUserControlIndex(index).value,
        };
        break;
      case 'userGroup':
        formData = {
          groupAssignee: this.assignedUserGroupControlIndex(index).value,
        };
        break;
    }
    this.patchActivity(activityId, formData)
  }

  /**
   * Updates activity.
   * @param activityId
   * @param formData
   */
  patchActivity(activityId, formData) {
    this.actvititeitenService.patchActivity(activityId, formData).subscribe(() => {
      this.assignUserForm.reset();
      this.users = null;
      this.openAssigneeEditField = null;
      this.fetchActivities();
    }, res =>  {
      this.reportError(res);
    })
  }

  /**
   * Sets activity on "finished"
   * @param activityId
   */
  closeActivity(activityId) {
    this.isLoading = true
    const formData = {
      status: "finished"
    }

    this.actvititeitenService.patchActivity(activityId, formData).subscribe(() => {
      this.showCloseActivityConfirmation = null;
      this.fetchActivities();
    }, res =>  {
      this.showCloseActivityConfirmation = null;
      this.reportError(res);
    })
  }

  /**
   * Deletes an activity.
   * @param activityId
   */
  deleteActivity(activityId) {
    this.isLoading = true

    this.actvititeitenService.deleteActivity(activityId).subscribe(() => {
      this.showDeleteActivityConfirmation = null;
      this.fetchActivities();
    }, res =>  {
      this.showDeleteActivityConfirmation = null;
      this.reportError(res);
    })
  }

  /**
   * Updates the document for an activity.
   * @param activityId
   * @param {Document} document
   */
  patchActivityDocument(activityId, document: Document) {
    const formData = {
      document: document.url
    }
    this.actvititeitenService.patchActivity(activityId, formData).subscribe(() => {
      this.openDocumentUploadForm = null;
      this.fetchActivities();
    }, res =>  {
      this.openDocumentUploadForm = null;
      this.reportError(res);
    })
  }

  /**
   * Retrieve read link for document.
   * @param readUrl
   */
  readDocument(readUrl) {
    this.actvititeitenService.readDocument(readUrl).subscribe((res: ReadWriteDocument) => {
      window.open(res.magicUrl, "_self");
    })
  }

  /**
   * When closing activity is pressed.
   * @param i
   */
  onCloseActivityConfirmation(i) {
    this.showCloseActivityConfirmation = i;
    this.openAssigneeEditField = null;
    this.openNoteEditField = null;
    this.openNoteEditField = null;
  }

  /**
   * Gets called when te activity is either expanded or collapsed.
   * @param {Activity} activity
   */
  onToggleExpandedActivity(activity: Activity): void {
    this.expandedActivity = this.expandedActivity ? null : activity;
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param res
   */
  reportError(res) {
    this.errorMessage = res.error?.detail ? res.error.detail :
      res.error?.nonFieldErrors ? res.error.nonFieldErrors[0] : "Er is een fout opgetreden."
    this.isLoading = false;
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(res);
  }
}
