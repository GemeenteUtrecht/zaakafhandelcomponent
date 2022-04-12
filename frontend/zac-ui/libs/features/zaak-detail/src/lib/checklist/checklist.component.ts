import {Component, Input, OnChanges, OnInit} from '@angular/core';
import {FieldConfiguration, SnackbarService} from '@gu/components';
import {
  Checklist,
  ChecklistAnswer,
  ChecklistQuestion,
  ChecklistType,
  QuestionChoice,
  User,
  UserGroupDetail,
  UserSearchResult,
  Zaak
} from '@gu/models';
import {ChecklistService, UserService, ZaakService} from '@gu/services';
import {KetenProcessenService} from '../keten-processen/keten-processen.service';
import {FormGroup} from '@angular/forms';
import {HttpErrorResponse} from '@angular/common/http';


/**
 * <gu-checklist [bronorganisatie]="bronorganisatie" [identificatie]="identificatie"></gu-checklist>
 * FIXME: TOGGLEABLE FORMS DONT WORK
 *
 * Shows checklist.
 *
 * Requires bronorganisatie: string Input to identify the organisation.
 * Requires identificatie: string Input to identify the case (zaak).
 */
@Component({
  selector: 'gu-checklist',
  templateUrl: './checklist.component.html',
})
export class ChecklistComponent implements OnInit, OnChanges {
  /** @type {string} Input to identify the organisation. */
  @Input() bronorganisatie: string;

  /** @type {string} Input to identify the case (zaak). */
  @Input() identificatie: string;

  readonly errorMessage = 'Er is een fout opgetreden bij het laden van de checklist.'

  /** @type {boolean} Whether the API is loading. */
  isLoading = false;

  /** @type {boolean} Whether the form is submitting to the API. */
  isSubmitting = false;

  /** @type {ChecklistType} The checklist type. */
  checklistType: ChecklistType = null;

  /** @type {Checklist} The checklist. */
  checklist: Checklist = null;

  /** @type {FieldConfiguration[]} The checklist form. */
  checklistForm: FieldConfiguration[] = null;

  /** @type {User[]} */
  users: UserSearchResult[] = []

  /** @type {Group[]} */
  groups: UserGroupDetail[] = []

  /** @type {Zaak} The zaak object. */
  zaak: Zaak = null;

  /**
   * Constructor method.
   * @param {ChecklistService} checklistService
   * @param {KetenProcessenService} ketenProcessenService
   * @param {SnackbarService} snackbarService
   * @param {UserService} userService
   * @param {ZaakService} zaakService
   */
  constructor(
    private checklistService: ChecklistService,
    private ketenProcessenService: KetenProcessenService,
    private snackbarService: SnackbarService,
    private userService: UserService,
    private zaakService: ZaakService,
  ) {
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
  }

  /**
   * A lifecycle hook that is called when any data-bound property of a directive changes. Define an ngOnChanges() method
   * to handle the changes.
   */
  ngOnChanges(): void {
    this.getContextData();
  };

  //
  // Context.
  //

  /**
   * Fetches the properties to show in the form.
   */
  getContextData(): void {
    this.fetchChecklistData();
    this.fetchUsers();
    this.fetchGroups();
  }

  /**
   * Fetches the user.
   */
  fetchUsers(): void {
    this.ketenProcessenService.getAccounts('').subscribe((userSearch) => {
      this.users = userSearch.results;
      this.checklistForm = this.getChecklistForm();
    });
  }

  /**
   * Fetches the user.
   */
  fetchGroups(): void {
    this.ketenProcessenService.getUserGroups('').subscribe((userGroupList) => {
      this.groups = userGroupList.results;
      this.checklistForm = this.getChecklistForm();
    });
  }

  /**
   * Fetches the ChecklistTypes and Checklists, creates forms.
   */
  fetchChecklistData(): void {
    this.isLoading = true;
    const result = this.zaakService.retrieveCaseDetails(this.bronorganisatie, this.identificatie).subscribe(
      (zaak) => {
        this.zaak = zaak;

        this.checklistService.retrieveChecklistTypeAndRelatedQuestions(this.bronorganisatie, this.identificatie).subscribe(
          (checklistType: ChecklistType) => {
            this.checklistType = checklistType;

            this.checklistService.retrieveChecklistAndRelatedAnswers(this.bronorganisatie, this.identificatie).subscribe(
              (checklist: Checklist) => {
                this.checklist = checklist;
                this.checklistForm = this.getChecklistForm();
                this.isLoading = false;
              },
              this.handleError.bind(this)
            )
          },
          this.handleError.bind(this)
        );
      },
      this.reportError.bind(this)
    );
  }

  /**
   * Returns a FieldConfiguration[] (form) for a ChecklistType.
   * @return {FieldConfiguration[]}
   */
  getChecklistForm(): FieldConfiguration[] {
    const fieldConfigurations = this.checklistType?.questions.map((question: ChecklistQuestion) => {
      const answer = this.checklist?.answers.find((checklistAnswer) => checklistAnswer.question === question.question);

      return ({
        label: question.question,
        name: question.question,
        value: answer?.answer,
        choices: (question.isMultipleChoice)
          ? question.choices.map((questionChoice: QuestionChoice) => ({
            label: questionChoice.name,
            value: questionChoice.value,
          }))
          : null,
      });
    });

    return [
      ...(fieldConfigurations || []),
      {
        activeWhen: (formGroup: FormGroup) => !formGroup.getRawValue().groupAssignee,
        label: 'Toegewezen gebruiker',
        name: 'userAssignee',
        required: false,
        choices: this.users.map((user: UserSearchResult) => ({label: user.username, value: user.username})),
        value: this.checklist?.userAssignee?.username,
      },
      {
        activeWhen: (formGroup: FormGroup) => !formGroup.getRawValue().userAssignee,
        label: 'Toegewezen groep',
        name: 'groupAssignee',
        required: false,
        choices: this.groups.map((group: UserGroupDetail) => ({label: group.name, value: group.name})),
        value: this.checklist?.groupAssignee?.name,
      }
    ]
  }

  //
  // Events.
  //

  /**
   * Gets called when a checklist form is submitted.
   * @param {Object} data
   */
  submitForm(data): void {
    this.isSubmitting = true;

    const {userAssignee, groupAssignee, ...answerData} = data;
    const answers: ChecklistAnswer[] = Object.entries(answerData).map(([question, answer]) => ({
      question: question,
      answer: answer as string,
      created: new Date().toISOString()
    }));


    if (this.checklist) {
      this.checklistService.updateChecklistAndRelatedAnswers(this.bronorganisatie, this.identificatie, answers, userAssignee, groupAssignee).subscribe(
        this.fetchChecklistData.bind(this),
        this.reportError.bind(this),
        () => this.isSubmitting= false
      );
    } else {
      this.checklistService.createChecklistAndRelatedAnswers(this.bronorganisatie, this.identificatie, answers, userAssignee, groupAssignee).subscribe(
        this.fetchChecklistData.bind(this),
        this.reportError.bind(this),
        () => this.isSubmitting= false
      );
    }
  }

  //
  // Error handling.
  //

  /**
   * Handles an HttpErrorResponse.
   * @param {HttpErrorResponse} httpErrorResponse
   */
  handleError(httpErrorResponse: HttpErrorResponse) {
    if (httpErrorResponse.status === 404) {
      this.isLoading = false;
      return;
    }
    this.reportError(httpErrorResponse)
  }

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    const message = this.errorMessage;
    this.snackbarService.openSnackBar(message, 'Sluiten', 'warn');
    this.isLoading = false;
    console.error(error);
  }
}
