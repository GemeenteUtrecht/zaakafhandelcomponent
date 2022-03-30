import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { DatePipe } from '@angular/common';
import { TaskContextData } from '../../../../models/task-context';
import { ApplicationHttpClient } from '@gu/services';
import { FormArray, FormBuilder, FormControl, FormGroup, ValidationErrors, Validators } from '@angular/forms';
import { KetenProcessenService } from '../../keten-processen.service';
import { atleastOneValidator } from '@gu/utils';
import {ReadWriteDocument, UserGroupDetail, UserSearchResult} from "@gu/models";
import { ModalService, SnackbarService } from '@gu/components';

/**
 * <gu-config-adviseren-accorderen [taskContextData]="taskContextData"></gu-config-adviseren-accorderen>
 *
 * This is a configuration componenten for adviseren/accorderen tasks.
 *
 * Requires taskContextData: TaskContextData input for the form layout.
 *
 * Emits successReload: boolean after succesfully submitting the form.
 */
@Component({
  selector: 'gu-config-adviseren-accorderen',
  templateUrl: './adviseren-accorderen.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class AdviserenAccorderenComponent implements OnChanges {
  @Input() taskContextData: TaskContextData;

  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  readonly assignedUsersTitle = {
    advice: 'Adviseurs',
    approval: 'Accordeurs'
  }
  reviewType: 'advice' | 'approval';

  steps = 1;
  minDate = new Date();
  searchResultUsers: UserSearchResult[] = [];
  searchResultUserGroups: UserGroupDetail[] = [];

  assignUsersForm: FormGroup;

  isSubmitting: boolean;
  submitSuccess: boolean;
  errorMessage: string;

  constructor(
    private datePipe: DatePipe,
    private fb: FormBuilder,
    private http: ApplicationHttpClient,
    private modalService: ModalService,
    private ketenProcessenService: KetenProcessenService,
    private snackbarService: SnackbarService,
  ) {}

  //
  // Getters / setters.
  //

  get documents(): FormArray {
    return this.assignUsersForm.get('documents') as FormArray;
  };

  get assignedUsers(): FormArray {
    return this.assignUsersForm.get('assignedUsers') as FormArray;
  };

  get toelichting(): FormControl {
    return this.assignUsersForm.get('toelichting') as FormControl;
  };

  assignedUsersControl(index: number): FormControl {
    return this.assignedUsers.at(index).get('assignees').get('users') as FormControl;
  }

  assignedUserGroupControl(index: number): FormControl {
    return this.assignedUsers.at(index).get('assignees').get('userGroups') as FormControl;
  }

  assignedEmailNotificationControl(index: number): FormControl {
    return this.assignedUsers.at(index).get('emailNotification') as FormControl;
  }

  assignedDeadlineControl(index: number): FormControl {
    return this.assignedUsers.at(index).get('deadline') as FormControl;
  }

  extraStepControl(index: number): FormControl {
    return this.assignedUsers.at(index).get('extraStep') as FormControl;
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called when any data-bound property of a directive changes. Define an ngOnChanges() method
   * to handle the changes.
   */
  ngOnChanges(changes: SimpleChanges) {
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
      this.reviewType = this.taskContextData.context.reviewType;
      this.assignUsersForm = this.fb.group({
        documents: this.addDocumentCheckboxes(),
        assignedUsers: this.fb.array([this.addAssignUsersStep()]),
        toelichting: this.fb.control("", Validators.maxLength(4000))
      })
    }
  }

  //
  // Context.
  //

  /**
   * Send configuration data to API.
   * @param formData
   */
  putForm(formData) {
    this.ketenProcessenService.putTaskData(this.taskContextData.task.id, formData).subscribe(() => {
      this.isSubmitting = false;
      this.submitSuccess = true;
      this.successReload.emit(true);

      this.modalService.close('ketenprocessenModal');
    }, error => {
      this.isSubmitting = false;
      this.errorMessage = error.detail ? error.detail : "Er is een fout opgetreden";
      this.reportError(error);
    })
  }

  /**
   * Creates form controls for checkboxes.
   * @returns {FormArray}
   */
  addDocumentCheckboxes() {
    const arr = this.taskContextData.context.documents.map(() => {
      return this.fb.control(false);
    });
    return this.fb.array(arr, atleastOneValidator());
  }

  /**
   * Creates form group for steps.
   * @returns {FormGroup}
   */
  addAssignUsersStep() {
    return this.fb.group({
      deadline: [undefined, Validators.required],
      assignees: this.fb.group({
        users: [[]],
        userGroups: [[]],
      }, { validators: [this.atLeastOneAssignee]}),
      emailNotification: [false],
      extraStep: ['']
    })
  }

  /**
   * Validator for assignees.
   * @param {FormGroup} form
   * @returns {ValidationErrors}
   */
  atLeastOneAssignee(form: FormGroup): ValidationErrors {
    if (form.value["users"]?.length > 0 || form.value["userGroups"]?.length > 0) {
      return null
    }
    return { "error": "Minimaal één selectie benodigd." }
  }

  /**
   * Sets minimum deadline date for form group.
   * @param {number} index
   * @returns {Date}
   */
  assignedMinDateControl(index: number): Date {
    const today = new Date();
    if (this.assignedUsers.at(index - 1)) {
      const previousDeadline = this.assignedUsers.at(index - 1).get('deadline').value ? this.assignedUsers.at(index - 1).get('deadline').value : today;
      const dayAfterDeadline = new Date(previousDeadline);
      dayAfterDeadline.setDate(previousDeadline.getDate() + 1);
      return dayAfterDeadline;
    } else {
      return today
    }
  }

  //
  // Events.
  //

  /**
   * Adds a step to the form.
   * @param i
   */
  addStep(i) {
    if (this.extraStepControl(i).value) {
      this.steps++
      this.assignedUsers.push(this.addAssignUsersStep());
    } else {
      this.deleteStep();
    }
  }

  /**
   * Deletes last step in the form.
   */
  deleteStep() {
    this.steps--
    this.assignedUsers.removeAt(this.assignedUsers.length - 1);
  }

  /**
   * Redirects to url on click.
   * @param url
   */
  handleDocumentClick(url) {
    this.ketenProcessenService.readDocument(url).subscribe((res: ReadWriteDocument) => {
      window.open(res.magicUrl, "_blank");
    }, error => {
      this.errorMessage = error.detail ? error.detail : "Er is een fout opgetreden";
      this.reportError(error);
    });
  }

  /**
   * Searches for users.
    * @param searchInput
   */
  onSearchUsers(searchInput) {
    if (searchInput) {
      this.ketenProcessenService.getAccounts(searchInput).subscribe(res => {
        this.searchResultUsers = res.results;
      }, error => {
        this.errorMessage = error.detail ? error.detail : "Er is een fout opgetreden";
        this.reportError(error);
      })
    } else {
      this.searchResultUsers = [];
    }
  }

  /**
   * Searches for user groups.
   * @param searchInput
   */
  onSearchUserGroups(searchInput) {
    if (searchInput) {
      this.ketenProcessenService.getUserGroups(searchInput).subscribe(res => {
        this.searchResultUserGroups = res.results;
      }, error => {
        this.errorMessage = error.detail ? error.detail : "Er is een fout opgetreden";
        this.reportError(error);
      })
    } else {
      this.searchResultUserGroups = [];
    }
  }

  /**
   * Prepare form data to fit API.
   */
  submitForm() {
    this.isSubmitting = true;

    const selectedDocuments = this.documents.value
      .map((checked, i) => checked ? this.taskContextData.context.documents[i].url : null)
      .filter(v => v !== null);

    const assignedUsers = this.assignedUsers.controls
      .map( (step, i) => {
        const deadline = this.datePipe.transform(this.assignedDeadlineControl(i).value, "yyyy-MM-dd");
        const users = this.assignedUsersControl(i).value ? this.assignedUsersControl(i).value : [];
        const userGroups = this.assignedUserGroupControl(i).value ? this.assignedUserGroupControl(i).value : [];
        const emailNotification = this.assignedEmailNotificationControl(i).value ? this.assignedEmailNotificationControl(i).value : false;

        return {
          deadline: deadline,
          userAssignees: users,
          groupAssignees: userGroups,
          emailNotification: emailNotification
        }
      })

    const toelichting = this.toelichting.value;
    const formData = {
      form: this.taskContextData.form,
      assignedUsers: assignedUsers,
      selectedDocuments: selectedDocuments,
      toelichting: toelichting
    };

    this.putForm(formData);
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }

}
