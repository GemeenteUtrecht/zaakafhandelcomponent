import { Component, Input, OnInit } from '@angular/core';
import { ActiviteitenService } from './activiteiten.service';
import { Activity } from '../../models/activity';
import { first } from 'rxjs/operators';
import { User, ShortDocument } from '@gu/models';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { Result } from '../../models/user-search';
import { Document, ReadWriteDocument } from '../documenten/documenten.interface';

@Component({
  selector: 'gu-activiteiten',
  templateUrl: './activiteiten.component.html',
  styleUrls: ['./activiteiten.component.scss']
})
export class ActiviteitenComponent implements OnInit {
  @Input() mainZaakUrl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() activityData: Activity[];
  @Input() currentUser: User;
  currentUserFullname: string;

  activityForm: FormGroup;
  addActivityForm: FormGroup;
  assignUserForm: FormGroup;

  users: Result[] = [];

  ongoingData: Activity[] = [];
  finishedData: Activity[] = [];

  isLoading: boolean;
  hasError: boolean;
  errorMessage: string;
  openNoteEditField: number;
  openAssigneeEditField: number;
  openDocumentUploadForm: number;

  eventIsExpanded: number;

  showAddActivityButton: boolean;
  showCloseActivityConfirmation: number;
  showDeleteActivityConfirmation: number;

  isSubmitting: boolean;

  activityDocs: ShortDocument[] = [];
  ongoingActivityDocs: ShortDocument[] = [];
  finishedActivityDocs: ShortDocument[] = [];
  isFetchingDocuments: boolean;

  constructor(private actvititeitenService: ActiviteitenService,
              private fb: FormBuilder) { }

  ngOnInit(): void {
    this.activityForm = this.fb.group({
      notes: this.fb.array(this.addNotesControl(this.activityData))
    })

    this.assignUserForm = this.fb.group({
      user: this.fb.array(this.addAssignUserControl(this.activityData))
    })

    this.addActivityForm = this.fb.group({
      name: this.fb.control("", Validators.required),
      remarks: this.fb.control(""),
    })

    this.isLoading = true;
    if (this.currentUser) {
      this.currentUserFullname = (this.currentUser.firstName && this.currentUser.lastName) ?
        `${this.currentUser.firstName} ${this.currentUser.lastName}` :
        (this.currentUser.firstName && !this.currentUser.lastName) ?
          this.currentUser.firstName : this.currentUser.username
    }
    this.formatActivityData(this.activityData);
    this.fetchDocuments(this.activityData);
    this.isLoading = false;
  }

  addNotesControl(data) {
    return data.map( () => this.fb.control("", Validators.required) )
  }

  addAssignUserControl(data) {
    return data.map( () => this.fb.control("", Validators.required) )
  }

  get addActivityName(): FormControl {
    return this.addActivityForm.get('name') as FormControl;
  };

  get addActivityRemarks(): FormControl {
    return this.addActivityForm.get('remarks') as FormControl;
  };

  get notesControl(): FormArray {
    return this.activityForm.get('notes') as FormArray;
  };

  get assignUserControl(): FormArray {
    return this.assignUserForm.get('user') as FormArray;
  };

  notes(index: number): FormControl {
    return this.notesControl.at(index) as FormControl;
  }

  assignedUser(index: number): FormControl {
    return this.assignUserControl.at(index) as FormControl;
  }

  onSearch(searchInput) {
    this.actvititeitenService.getAccounts(searchInput).subscribe(res => {
      this.users = res.results.map(result => ({
        ...result,
        name: (result.firstName && result.lastName) ?
          `${result.firstName} ${result.lastName}` :
          (result.firstName && !result.lastName) ?
            result.firstName : result.username
      }))
    })
  }

  fetchActivities() {
    if (this.mainZaakUrl) {
      this.actvititeitenService.getActivities(this.mainZaakUrl)
        .pipe(first())
        .subscribe(res => {
          this.activityData = res;
          this.formatActivityData(res);
          this.fetchDocuments(res);
          this.isLoading = false;
        });
    }
  }

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

  formatActivityData(activities: Activity[]) {
    this.ongoingData = activities.filter(activity => {
      return activity.status === 'on_going'
    })
    this.finishedData = activities.filter(activity => {
      return activity.status === 'finished'
    })
  }

  formatDocsData(activityDocs: ShortDocument[]) {
    this.ongoingActivityDocs = activityDocs.filter((activity, i) => {
      return this.activityData[i].status === 'on_going';
    })
    this.finishedActivityDocs = activityDocs.filter((activity, i) => {
      return this.activityData[i].status === 'on_going';
    })
  }

  createNewActivity() {
    this.isSubmitting = true;
    const formData = {
      zaak: this.mainZaakUrl,
      name: this.addActivityName.value,
      remarks: this.addActivityRemarks.value
    }

    this.actvititeitenService.postNewActivity(formData).subscribe(() => {
      this.isSubmitting = false;
      this.addActivityForm.reset();
      this.showAddActivityButton = false
      this.fetchActivities();
    }, res =>  {
      this.setError(res)
    })
  }

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
      this.setError(res)
    })
  }

  submitAssignUser(activityId, index) {
    this.isLoading = true
    const formData = {
      assignee: this.assignedUser(index).value
    }

    this.actvititeitenService.patchActivity(activityId, formData).subscribe(() => {
      this.assignUserForm.reset();
      this.openAssigneeEditField = null;
      this.fetchActivities();
    }, res =>  {
      this.setError(res);
    })
  }

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
      this.setError(res);
    })
  }

  deleteActivity(activityId) {
    this.isLoading = true

    this.actvititeitenService.deleteActivity(activityId).subscribe(() => {
      this.showDeleteActivityConfirmation = null;
      this.fetchActivities();
    }, res =>  {
      this.showDeleteActivityConfirmation = null;
      this.setError(res);
    })
  }

  patchActivityDocument(activityId, document: Document) {
    const formData = {
      document: document.url
    }
    this.actvititeitenService.patchActivity(activityId, formData).subscribe(() => {
      this.openDocumentUploadForm = null;
      this.fetchActivities();
    }, res =>  {
      this.openDocumentUploadForm = null;
      this.setError(res);
    })
  }

  readDocument(readUrl) {
    this.actvititeitenService.readDocument(readUrl).subscribe((res: ReadWriteDocument) => {
      window.open(res.magicUrl, "_blank");
    })
  }

  setError(res) {
    this.hasError = true;
    this.errorMessage = res.error?.detail ? res.error.detail : "Er is een fout opgetreden."
    this.isLoading = false;
  }
}
