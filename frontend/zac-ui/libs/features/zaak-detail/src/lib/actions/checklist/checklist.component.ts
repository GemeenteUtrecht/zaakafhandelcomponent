import { Component, EventEmitter, HostListener, Input, OnChanges, OnInit, Output, ViewChild } from '@angular/core';
import {FieldConfiguration, FieldsetConfiguration, SnackbarService} from '@gu/components';
import {
  Checklist,
  ChecklistAnswer,
  ChecklistQuestion,
  ChecklistType,
  Document,
  QuestionChoice,
  User,
  UserGroupDetail,
  UserSearchResult,
  Zaak
} from '@gu/models';
import {ChecklistService, DocumentenService, UserService, ZaakService} from '@gu/services';
import {KetenProcessenService} from '../keten-processen/keten-processen.service';
import {UntypedFormGroup} from '@angular/forms';
import {HttpErrorResponse} from '@angular/common/http';
import {FormComponent} from '@gu/components';

/**
 * <gu-checklist [bronorganisatie]="bronorganisatie" [identificatie]="identificatie"></gu-checklist>
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
  @ViewChild(FormComponent) formComponent: FormComponent;

  /** @type {string} Input to identify the organisation. */
  @Input() zaak: Zaak = null;

  @Output() isChecklistAvailable: EventEmitter<boolean> = new EventEmitter<boolean>();

  /**
   * Show message when checklist has unsaved changes
   * @param $event
   */
  @HostListener('window:beforeunload', ['$event'])
  unloadNotification($event: any): void {
    if (this.isInEditMode) {
      $event.preventDefault();
      $event.returnValue = '';
    }
  }

  readonly errorMessage = 'Er is een fout opgetreden bij het laden van de takenlijst.'

  /** @type {boolean} Whether the API is loading. */
  isLoading = false;
  isLocking = false;
  isInEditMode = false;

  /** @type {boolean} Whether the form is submitting to the API. */
  isSubmitting = false;

  /** @type {ChecklistType} The checklist type. */
  checklistType: ChecklistType = null;

  /** @type {Checklist} The checklist. */
  checklist: Checklist = null;

  /** @type {FieldConfiguration[]} The checklist form. */
  checklistForm: FieldConfiguration[] = null;

  /** @type {Object} */
  documents: { [index: string]: Document } = {};

  /** @type {User[]} */
  users: UserSearchResult[] = []

  /** @type {Group[]} */
  groups: UserGroupDetail[] = []

  /** @type {number} */
  totalDocumentsAdded: number;

  /** @type {boolean} Whether a checklist is available for the case*/
  hasChecklist = false;

  /**
   * Constructor method.
   * @param {ChecklistService} checklistService
   * @param {DocumentenService} documentenService
   * @param {KetenProcessenService} ketenProcessenService
   * @param {SnackbarService} snackbarService
   * @param {UserService} userService
   * @param {ZaakService} zaakService
   */
  constructor(
    private checklistService: ChecklistService,
    private documentenService: DocumentenService,
    private ketenProcessenService: KetenProcessenService,
    private snackbarService: SnackbarService,
    private userService: UserService,
    private zaakService: ZaakService,
  ) {
  }

  /**
   * Whether user can force edit a closed case.
   * @returns {boolean}
   */
  get canForceEdit(): boolean {
    return !this.zaak.resultaat || this.zaak.kanGeforceerdBijwerken;
  }

  /**
   * Whether all documents for the answers are retrieved
   * @returns {boolean}
   */
  get finishedLoadingDocuments(): boolean {
    if (this.totalDocumentsAdded) {
      return Object.keys(this.documents).length === this.totalDocumentsAdded;
    }
    return true
}

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.getContextData();
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
      if (this.checklist && this.checklistType) {
        this.checklistForm = this.getChecklistForm();
      }
    });
  }

  /**
   * Fetches the user.
   */
  fetchGroups(): void {
    this.ketenProcessenService.getUserGroups('').subscribe((userGroupList) => {
      this.groups = userGroupList.results;
      if (this.checklist && this.checklistType) {
        this.checklistForm = this.getChecklistForm();
      }
    });
  }

  /**
   * Fetches the ChecklistTypes and Checklists, creates forms.
   */
  fetchChecklistData(): void {
    this.isLoading = true;

    this.checklistService.retrieveChecklistTypeAndRelatedQuestions(this.zaak.bronorganisatie, this.zaak.identificatie).subscribe(
      (checklistType: ChecklistType) => {
        this.isChecklistAvailable.emit(true);
        this.checklistType = checklistType;
        this.checklistForm = this.getChecklistForm();

        this.checklistService.retrieveChecklistAndRelatedAnswers(this.zaak.bronorganisatie, this.zaak.identificatie).subscribe(
          (checklist: Checklist) => {
            this.hasChecklist = true;
            const addedDocuments = checklist.answers.filter((checklistAnswer: ChecklistAnswer) => checklistAnswer.document);
            this.totalDocumentsAdded = addedDocuments.length;

            addedDocuments.forEach((checklistAnswer: ChecklistAnswer) => {
              this.documentenService.getDocument(checklistAnswer.document).subscribe(
                (document: Document) => {
                  this.documents[checklistAnswer.question] = document
                  this.isLoading = false;
                  this.checklistForm = this.getChecklistForm();
                }, this.reportError.bind(this)
              );
            })
            this.checklist = checklist;
            this.checklistForm = this.getChecklistForm();
            this.isLoading = false;
          },
          this.handleError.bind(this)
        )
      },
      this.handleError.bind(this)
    );
  }

  /**
   * Returns a FieldConfiguration[] (form) for a ChecklistType.
   * @return {FieldConfiguration[]}
   */
  getChecklistForm(): FieldConfiguration[] {
    const fieldConfigurations = this.checklistType?.questions
      .sort((a: ChecklistQuestion, b: ChecklistQuestion) => a.order - b.order)
      .reduce((acc, question: ChecklistQuestion) => {
        const answer = this.checklist?.answers.find((checklistAnswer) => checklistAnswer.question === question.question);

        return [...acc, {
          label: 'Antwoord',
          name: question.question,
          required: false,
          value: answer?.answer,
          choices: (question.isMultipleChoice)
            ? question.choices.map((questionChoice: QuestionChoice) => ({
              label: questionChoice.name,
              value: questionChoice.value,
            }))
            : null,
          readonly: !this.canForceEdit
        }, {
          label: `Voeg opmerking toe`,
          name: `__remarks_${question.question}`,
          format: 'long',
          required: false,
          value: answer?.remarks,
          readonly: !this.canForceEdit
        }, {
          label: `Document`,
          name: `__document_${question.question}`,
          required: false,
          type: 'document',
          value: this.documents[question.question],
          readonly: !this.canForceEdit
        }, {
          activeWhen: (formGroup: UntypedFormGroup) => !formGroup.getRawValue()[`__groupAssignee_${question.question}`],
          label: `Toegewezen gebruiker`,
          name: `__userAssignee_${question.question}`,
          required: false,
          choices: this.users.map((user: UserSearchResult) => ({label: user.fullName || user.username, value: user.username})),
          value: answer?.userAssignee?.username,
          readonly: !this.canForceEdit
        },
          {
            activeWhen: (formGroup: UntypedFormGroup) => !formGroup.getRawValue()[`__userAssignee_${question.question}`],
            label: `Toegewezen groep`,
            name: `__groupAssignee_${question.question}`,
            required: false,
            choices: this.groups.map((group: UserGroupDetail) => ({label: group.name, value: group.name})),
            value: answer?.groupAssignee?.name,
            readonly: !this.canForceEdit
          }];
      }, []);

    return fieldConfigurations;
  }

  /**
   * Returns fieldsets based on questions.
   */
  getFieldsets() {
    return this.checklistType?.questions.map((question: ChecklistQuestion): FieldsetConfiguration => {
      const answer = this.checklist?.answers.find((checklistAnswer) => checklistAnswer.question === question.question);
      const value = answer?.answer
      const description = (value!==undefined && question.choices.length)
        ? question.choices[parseInt(value, 10)]?.name || value
        : value

      return ({
        description: description || '-',
        label: question.question,
        keys: [
          question.question,
          `__remarks_${question.question}`,
          `__document_${question.question}`,
          `__userAssignee_${question.question}`,
          `__groupAssignee_${question.question}`,
        ]
      });
    })
  }

  /**
   * Gets called when a checklist form is submitted.
   * @param {Object} answerData
   * @param {boolean} isFormSubmit
   */
  submitForm(answerData, isFormSubmit?): void {
    const answers: ChecklistAnswer[] = Object.entries(answerData)
      .filter(([key, value]) => !key.match(/^__/))
      .map(([question, answer]) => {
        const documentKey = `__document_${question}`;
        const document = answerData[documentKey];
        const documentUrl = document?.url;

        const remarksKey = `__remarks_${question}`;
        const remarks = answerData[remarksKey];

        const userAssigneeKey = `__userAssignee_${question}`;
        const userAssignee = answerData[userAssigneeKey];

        const groupAssigneeKey = `__groupAssignee_${question}`;
        const groupAssignee = answerData[groupAssigneeKey];

        return ({
          answer: answer as string || '',
          document: documentUrl,
          question: question,
          remarks: remarks || '',
          userAssignee: userAssignee,
          groupAssignee: groupAssignee,
        });
      });

    if (this.checklist) {
      this.checklistService.updateChecklistAndRelatedAnswers(this.zaak.bronorganisatie, this.zaak.identificatie, answers).subscribe(() =>{
          if (isFormSubmit) {
            this.unlockChecklist(false);
            this.fetchChecklistData();
          } else {
            this.lockChecklist(true);
          }
          this.hasChecklist = false;
          this.documents = {};
        },
        this.reportError.bind(this),
        () => this.isSubmitting = false
      );
    } else {
      this.checklistService.createChecklistAndRelatedAnswers(this.zaak.bronorganisatie, this.zaak.identificatie, answers).subscribe(() =>{
        if (isFormSubmit) {
          this.unlockChecklist(false);
          this.fetchChecklistData()
        } else {
          this.lockChecklist(true);
        }
      },
      this.reportError.bind(this),
        () => this.isSubmitting = false
      )
    }
  }

  //
  // Events.
  //

  /**
   * Lock or unlock checklist according to event
   * @param formIsInEditMode
   */
  onClickEditButton(formIsInEditMode) {
    this.isLocking = true;
    this.isInEditMode = !formIsInEditMode;
    if (formIsInEditMode) {
      this.unlockChecklist(formIsInEditMode);
    } else {
      this.lockChecklist(false);
    }
  }

  lockChecklist(formIsInEditMode) {
    this.isLocking = true
    this.checklistService.lockChecklist(this.zaak.bronorganisatie, this.zaak.identificatie).subscribe(() =>
      {
        this.isLocking = false;
        if (!formIsInEditMode) {
          this.formComponent.switchToggle();
        }
      },
      error => {
        this.isLocking = false;
        this.reportError(error);
      }
    )
  }

  unlockChecklist(formIsInEditMode) {
    this.isLocking = true
    this.checklistService.unLockChecklist(this.zaak.bronorganisatie, this.zaak.identificatie).subscribe(() =>
      {
        this.isLocking = false;
        this.formComponent.switchToggle();
      },
      error => {
        this.isLocking = false;
        if (formIsInEditMode) {
          this.formComponent.switchToggle();
        }
        this.reportError(error);
      }
    )
  }

  /**
   * Submit form
   * @param answerData
   */
  onSubmitForm(answerData): void {
    this.isSubmitting = true;
    this.submitForm(answerData, true);
  }

  /**
   * Auto save form
   * @param answerData
   */
  onAutoSave(answerData): void {
    this.submitForm(answerData);
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
    } else if (httpErrorResponse.status === 403) {
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
    let message =
      error.error?.value
      ? error.error?.value[0]
      : error?.error?.detail || error?.error.reason || error?.error[0]?.reason || error?.error.nonFieldErrors?.join(', ') || this.errorMessage;
    if (error.status === 400) {
      message = error.error ? error.error[0] : this.errorMessage;
      this.formComponent.switchToggle();
    }
    this.snackbarService.openSnackBar(message, 'Sluiten', 'warn');
    this.isLoading = false;
    this.isSubmitting = false;
    this.isLocking = false;
    console.error(error);
  }
}
