import {Component, Input, OnChanges, OnInit} from '@angular/core';
import {FieldConfiguration, SnackbarService} from '@gu/components';
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
import {FormGroup} from '@angular/forms';
import {HttpErrorResponse} from '@angular/common/http';


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

  /** @type {Object} */
  documents: { [index: string]: Document } = {};

  /** @type {User[]} */
  users: UserSearchResult[] = []

  /** @type {Group[]} */
  groups: UserGroupDetail[] = []

  /** @type {Zaak} The zaak object. */
  zaak: Zaak = null;

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

    const result = this.zaakService.retrieveCaseDetails(this.bronorganisatie, this.identificatie).subscribe(
      (zaak) => {
        this.zaak = zaak;

        this.checklistService.retrieveChecklistTypeAndRelatedQuestions(this.bronorganisatie, this.identificatie).subscribe(
          (checklistType: ChecklistType) => {
            this.checklistType = checklistType;
            this.checklistForm = this.getChecklistForm();

            this.checklistService.retrieveChecklistAndRelatedAnswers(this.bronorganisatie, this.identificatie).subscribe(
              (checklist: Checklist) => {
                checklist.answers.filter((checklistAnswer: ChecklistAnswer) => checklistAnswer.document)
                  .forEach((checklistAnswer: ChecklistAnswer) => {
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
      },
      this.reportError.bind(this)
    );
  }

  /**
   * Returns a FieldConfiguration[] (form) for a ChecklistType.
   * @return {FieldConfiguration[]}
   */
  getChecklistForm(): FieldConfiguration[] {
    const fieldConfigurations = this.checklistType?.questions.reduce((acc, question: ChecklistQuestion) => {
      const answer = this.checklist?.answers.find((checklistAnswer) => checklistAnswer.question === question.question);

      return [...acc, {
        label: question.question,
        name: question.question,
        required: false,
        value: answer?.answer,
        choices: (question.isMultipleChoice)
          ? question.choices.map((questionChoice: QuestionChoice) => ({
            label: questionChoice.name,
            value: questionChoice.value,
          }))
          : null,
      }, {
        label: `Voeg opmerking toe bij: ${question.question}`,
        name: `__remarks_${question.question}`,
        required: false,
        value: answer?.remarks,
      }, {
        label: `Voeg document toe bij: ${question.question}`,
        name: `__document_${question.question}`,
        required: false,
        type: 'document',
        value: this.documents[question.question]
      }];
    }, []);

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
    ];
  }

  //
  // Events.
  //

  /**
   * Gets called when a checklist form is submitted.
   * @param {Object} data
   */
  onSubmitForm(data): void {
    this.isSubmitting = true;

    const {userAssignee, groupAssignee, ...answerData} = data;
    const answers: ChecklistAnswer[] = Object.entries(answerData)
      .filter(([key, value]) => !key.match(/^__/))
      .map(([question, answer]) => {
        const documentKey = `__document_${question}`;
        const document = answerData[documentKey];
        const documentUrl = document?.url;

        const remarksKey = `__remarks_${question}`;
        const remarks = answerData[remarksKey];

        return ({
          answer: answer as string || '',
          created: new Date().toISOString(),
          document: documentUrl,
          question: question,
          remarks: remarks || '',
        });
      });


    if (this.checklist) {
      this.checklistService.updateChecklistAndRelatedAnswers(this.bronorganisatie, this.identificatie, answers, userAssignee, groupAssignee).subscribe(
        this.fetchChecklistData.bind(this),
        this.reportError.bind(this),
        () => this.isSubmitting = false
      );
    } else {
      this.checklistService.createChecklistAndRelatedAnswers(this.bronorganisatie, this.identificatie, answers, userAssignee, groupAssignee).subscribe(
        this.fetchChecklistData.bind(this),
        this.reportError.bind(this),
        () => this.isSubmitting = false
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
