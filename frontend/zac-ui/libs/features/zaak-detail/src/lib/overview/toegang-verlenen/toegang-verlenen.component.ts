import { Component, EventEmitter, Input, OnChanges, OnInit, Output } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { Observable } from 'rxjs';
import { UserSearchResult, UserSearch, Zaak } from '@gu/models';
import { ApplicationHttpClient } from '@gu/services';

@Component({
  selector: 'gu-toegang-verlenen',
  templateUrl: './toegang-verlenen.component.html',
  styleUrls: ['./toegang-verlenen.component.scss']
})
export class ToegangVerlenenComponent implements OnInit, OnChanges {
  @Input() zaak: Zaak;
  @Output() reload: EventEmitter<any> = new EventEmitter<any>();

  users: UserSearchResult[] = [];
  requesterUser: UserSearchResult;

  grantAccessForm: FormGroup;
  isLoading: boolean;
  isSubmitting: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;

  submitResult: any;
  submitSuccess: boolean;

  constructor(
    private fb: FormBuilder,
    private http: ApplicationHttpClient
  ) { }

  ngOnInit(): void {
    this.grantAccessForm = this.fb.group({
      requester: this.fb.control("", Validators.required),
    })
  }

  ngOnChanges() {
    this.submitSuccess = false;
  }

  get requester(): FormControl {
    return this.grantAccessForm.get('requester') as FormControl;
  };

  onSearch(searchInput) {
    this.getAccounts(searchInput).subscribe(res => {
      this.users = res.results;
    })
  }

  submitForm() {
    this.isSubmitting = true;
    this.users.forEach(user => {
      if (user.username === this.requester.value) {
        this.requesterUser = user;
      }
    })
    const formData = {
      requester: this.requester.value,
      zaak: this.zaak.url
    }
    this.postAccess(formData).subscribe( res => {
      this.submitResult = {
        username: res.requester,
        name: this.requesterUser
      }
      this.submitSuccess = true;
      this.grantAccessForm.reset();
      this.submitHasError = false;
      this.isSubmitting = false;
      this.reload.emit();
    }, error => {
      this.submitHasError = true;
      console.error(error);
      this.submitErrorMessage =
        error?.error?.detail ? error.error.detail
          : error?.error?.nonFieldErrors ? error.error?.nonFieldErrors[0]
          : 'Er is een fout opgetreden'
      this.isSubmitting = false;
    })
  }

  getAccounts(searchInput: string): Observable<UserSearch> {
    const endpoint = encodeURI(`/api/accounts/users?search=${searchInput}`);
    return this.http.Get<UserSearch>(endpoint);
  }

  postAccess(formData) {
    const endpoint = encodeURI('/api/accounts/cases/access');
    return this.http.Post<any>(endpoint, formData)
  }

}
