import { Component, Input, OnInit } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { Activity } from '../../models/activity';
import { first } from 'rxjs/operators';
import { User } from '@gu/models';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { Result, UserSearch } from '../../models/user-search';

@Component({
  selector: 'gu-activiteiten',
  templateUrl: './activiteiten.component.html',
  styleUrls: ['./activiteiten.component.scss']
})
export class ActiviteitenComponent implements OnInit {
  @Input() mainZaakUrl: string;
  @Input() activityData: Activity[];
  @Input() currentUser: User;
  currentUserFullname: string;

  activityForm: FormGroup;

  users: Result[] = [];

  ongoingData: Activity[] = [];
  finishedData: Activity[] = [];

  isLoading: boolean;
  hasError: boolean;
  errorMessage: string;

  openNoteEditField: number;
  openAssigneeEditField: number;
  eventIsExpanded: number;

  constructor(private http: ApplicationHttpClient,
              private fb: FormBuilder) {
    this.activityForm = this.fb.group({
      activityId: this.fb.control("", Validators.required),
      notes: this.fb.control("", Validators.required),
    })
  }

  ngOnInit(): void {
    this.isLoading = true;
    if (this.currentUser) {
      this.currentUserFullname = (this.currentUser.firstName && this.currentUser.lastName) ?
        `${this.currentUser.firstName} ${this.currentUser.lastName}` :
        (this.currentUser.firstName && !this.currentUser.lastName) ?
          this.currentUser.firstName : this.currentUser.username
    }
    this.formatActivityData(this.activityData);
    this.isLoading = false;
  }

  onSearch(searchInput) {
    this.getAccounts(searchInput).subscribe(res => {
      this.users = res.results.map(result => ({
        ...result,
        name: (result.firstName && result.lastName) ?
          `${result.firstName} ${result.lastName}` :
          (result.firstName && !result.lastName) ?
            result.firstName : result.username
      }))
    })
  }

  getAccounts(searchInput: string): Observable<UserSearch>{
    const endpoint = encodeURI(`/api/accounts/users?search=${searchInput}`);
    return this.http.Get<UserSearch>(endpoint);
  }

  get activityId(): FormControl {
    return this.activityForm.get('activityId') as FormControl;
  };

  get notes(): FormControl {
    return this.activityForm.get('notes') as FormControl;
  };

  fetchActivities() {
    if (this.mainZaakUrl) {
      this.getActivities()
        .pipe(first())
        .subscribe(res => {
          this.activityData = res;
          this.formatActivityData(res);
          this.isLoading = false;
        });
    }
  }

  formatActivityData(activities: Activity[]) {
    this.ongoingData = activities.filter(activity => {
      return activity.status === 'on_going'
    })
    this.finishedData = activities.filter(activity => {
      return activity.status === 'finished'
    })
  }

  submitNotes(activityId) {
    this.isLoading = true
    this.activityId.patchValue(activityId);
    const formData = {
      activity: this.activityId.value,
      notes: this.notes
    }

    this.postNotes(formData).subscribe(() => {
      this.fetchActivities();
    }, res =>  {
      this.hasError = true;
      this.errorMessage = res.error.detail ? res.error.detail : "Er is een fout opgetreden."
      this.isLoading = false;
    })

  }

  getActivities(): Observable<Activity[]> {
    const endpoint = `/activities/api/activities?zaak=${this.mainZaakUrl}`;
    return this.http.Get<Activity[]>(endpoint);
  }

  postNotes(formData): Observable<any> {
    return this.http.Post<any>(encodeURI('/activities/api/events'), formData);
  }


}
