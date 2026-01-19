import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild } from '@angular/core';
import { DatePipe } from '@angular/common';
import { TaskContextData } from '../../../../../models/task-context';
import { ApplicationHttpClient, ZaakService } from '@gu/services';
import { UntypedFormArray, UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, ValidationErrors, Validators } from '@angular/forms';
import { KetenProcessenService } from '../../keten-processen.service';
import {
  Document,
  ListDocuments,
  RowData,
  Table,
  UserGroupDetail,
  UserSearchResult,
} from '@gu/models';
import { ModalService, PaginatorComponent, SnackbarService } from '@gu/components';
import { KownslSummaryComponent } from '../../../adviseren-accorderen/kownsl-summary.component';
import { MatCheckboxChange } from '@angular/material/checkbox';

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
  @ViewChild(PaginatorComponent) paginator: PaginatorComponent;
  @Input() taskContextData: TaskContextData;
  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();
  @ViewChild(KownslSummaryComponent) kownslSummaryComponent: KownslSummaryComponent;

  readonly assignedUsersTitle = {
    advice: 'Adviseurs',
    approval: 'Accordeurs'
  }
  reviewType: 'advice' | 'approval';
  tableHead = [
    '',
    'Bestandsnaam',
    'Versie',
    'Auteur',
    'Informatieobjecttype',
    'Vertrouwelijkheidaanduiding',
  ]

  tableData: Table = new Table(this.tableHead, []);
  page = 1;

  sortValue: any;
  paginatedDocsData: ListDocuments;
  documentsData: any;
  selectedDocuments: string[] = [];
  steps = 1;
  minDate = new Date();
  searchResultUsers: UserSearchResult[];
  searchResultUserGroups: UserGroupDetail[];

  assignUsersForm: UntypedFormGroup;

  isSubmitting: boolean;
  submitSuccess: boolean;
  errorMessage: string;
  error: any;
  selectedProperties: string[] = [];

  constructor(
    private datePipe: DatePipe,
    private fb: UntypedFormBuilder,
    private http: ApplicationHttpClient,
    private modalService: ModalService,
    private ketenProcessenService: KetenProcessenService,
    private snackbarService: SnackbarService,
    private zaakService: ZaakService,
  ) {}

  //
  // Getters / setters.
  //

  get assignedUsers(): UntypedFormArray {
    return this.assignUsersForm.get('assignedUsers') as UntypedFormArray;
  };

  get toelichting(): UntypedFormControl {
    return this.assignUsersForm.get('toelichting') as UntypedFormControl;
  };

  assignedUsersControl(index: number): UntypedFormControl {
    return this.assignedUsers.at(index).get('assignees').get('users') as UntypedFormControl;
  }

  assignedUserGroupControl(index: number): UntypedFormControl {
    return this.assignedUsers.at(index).get('assignees').get('userGroups') as UntypedFormControl;
  }

  assignedEmailNotificationControl(index: number): UntypedFormControl {
    return this.assignedUsers.at(index).get('emailNotification') as UntypedFormControl;
  }

  assignedDeadlineControl(index: number): UntypedFormControl {
    return this.assignedUsers.at(index).get('deadline') as UntypedFormControl;
  }

  extraStepControl(index: number): UntypedFormControl {
    return this.assignedUsers.at(index)?.get('extraStep') as UntypedFormControl;
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
      const predefinedUsersArray = [this.addAssignUsersStep(true)];

      this.assignUsersForm = this.fb.group({
        assignedUsers: this.fb.array(predefinedUsersArray),
        toelichting: this.fb.control("", [Validators.maxLength(4000)])
      })
      this.selectedDocuments = this.taskContextData.context.previouslySelectedDocuments;
      this.selectedProperties = this.taskContextData.context.previouslySelectedZaakeigenschappen.length > 0 ?
        this.taskContextData.context.previouslySelectedZaakeigenschappen :
        this.taskContextData.context.zaakeigenschappen.map(doc => doc.url)
      this.fetchDocuments();
      this.checkPredefinedAssignees();
      this.addPreviouslyAssignedUsersStep();
    }
  }

  //
  // Context.
  //

  fetchDocuments(page = 1, sortValue?) {
    this.zaakService.listTaskDocuments(this.taskContextData.context.documentsLink, page, sortValue).subscribe(data => {
      this.tableData = this.formatTableData(data.results);
      this.paginatedDocsData = data;
      this.documentsData = data.results;
    });
  }

  formatTableData(data) {
    const tableData: Table = new Table(this.tableHead, []);
    tableData.bodyData = data.map((element: Document) => {
      const cellData: RowData = {
        cellData: {
          checkbox: {
            type: 'checkbox',
            checked: true,
            value: element.url
          },
          bestandsnaam: {
            type: 'text',
            label: element.titel,
          },
          versie: {
            type: 'text',
            style: 'no-minwidth',
            label: String(element.versie)
          },
          auteur: element.auteur,
          type: element.informatieobjecttype['omschrijving'],
          vertrouwelijkheidaanduiding: {
            type: 'text',
            label: element.vertrouwelijkheidaanduiding,
          },
        }
      }
      return cellData;
    })

    return tableData
  }

  /**
   * Send configuration data to API.
   * @param formData
   */
  putForm(formData) {
    this.ketenProcessenService.putTaskData(this.taskContextData.task.id, formData).subscribe(() => {
      this.isSubmitting = false;
      this.submitSuccess = true;
      this.successReload.emit(true);
      this.kownslSummaryComponent.update();
    }, error => {
      this.isSubmitting = false;
      this.errorMessage = error.error.detail ? error.error.detail : "Er is een fout opgetreden";
      this.error = error.error;
      this.reportError(error);
    })
  }

  /**
   * Creates form group for steps.
   * @returns {FormGroup}
   */
  addAssignUsersStep(isFirstStep?: boolean) {
    let userAssignees = [];
    let groupAssignees = [];
    let hasExtraStep = false;

    if (isFirstStep) {
      userAssignees = this.taskContextData.context.camundaAssignedUsers.userAssignees.map(userAssignee => userAssignee.username);
      groupAssignees = this.taskContextData.context.camundaAssignedUsers.groupAssignees.map(groupAssignee => groupAssignee.name);
      hasExtraStep = userAssignees.length > 0 || groupAssignees.length > 0;
      if (userAssignees.length > 0 || groupAssignees.length > 0) {
        this.addAssignUsersStep();
      }
      return this.fb.group({
        deadline: [undefined, Validators.required],
        assignees: this.fb.group({
          users: [userAssignees],
          userGroups: [groupAssignees],
        }, { validators: [this.atLeastOneAssignee]}),
        emailNotification: [true],
        extraStep: [hasExtraStep]
      })
    } else {
      return this.fb.group({
        deadline: [undefined, Validators.required],
        assignees: this.fb.group({
          users: [userAssignees],
          userGroups: [groupAssignees],
        }, { validators: [this.atLeastOneAssignee]}),
        emailNotification: [true],
        extraStep: ['']
      })
    }
  }

  /**
   * Create steps and add values for previous configs.
   */
  addPreviouslyAssignedUsersStep() {
    // Check previously assigned users
    if (this.taskContextData.context.previouslyAssignedUsers.length > 0) {
      let startIndex = 0
      this.taskContextData.context.previouslyAssignedUsers.forEach((user, i) => {
        if ((this.taskContextData.context.camundaAssignedUsers.userAssignees.length === 0 && this.taskContextData.context.camundaAssignedUsers.groupAssignees.length === 0)) {
          if (i+1 < this.taskContextData.context.previouslyAssignedUsers.length) {
            this.addStep(i, true)
          }
        } else {
          this.addStep(i, true)
        }
      })

      // Check camunda pre-assigned users
      if (this.taskContextData.context.camundaAssignedUsers.userAssignees.length > 0 || this.taskContextData.context.camundaAssignedUsers.groupAssignees.length > 0 ) {
        startIndex = 1;
      }

      // Add previously assigned users to search result to fill <gu-multiselect> with items
      this.searchResultUsers = [].concat(...this.taskContextData.context.previouslyAssignedUsers.map(obj => obj.userAssignees));
      this.searchResultUserGroups = [].concat(...this.taskContextData.context.previouslyAssignedUsers.map(obj => obj.groupAssignees));

      // Update step values according to previous configuration
      this.taskContextData.context.previouslyAssignedUsers.forEach((p, index) => {
        const userAssignees = p.userAssignees.map(userAssignee => userAssignee.username);
        const groupAssignees = p.groupAssignees.map(groupAssignee => groupAssignee.name);

        this.assignedUsersControl(startIndex + index).patchValue(userAssignees);
        this.assignedUserGroupControl(startIndex + index).patchValue(groupAssignees);
        this.assignedEmailNotificationControl(startIndex + index).patchValue(p.emailNotification);
        this.assignedDeadlineControl(startIndex + index).setValue(p.deadline);
        this.extraStepControl(startIndex + index)?.patchValue(index+1 < this.taskContextData.context.previouslyAssignedUsers.length);
      })

    }
  }

  /**
   * Disable fields if preconfigure
   */
  checkPredefinedAssignees() {
    if (this.taskContextData.context.camundaAssignedUsers.userAssignees.length > 0 || this.taskContextData.context.camundaAssignedUsers.groupAssignees.length > 0 ) {
      this.assignedUsersControl(0).disable();
      this.assignedUserGroupControl(0).disable();
    }
  }

  /**
   * Validator for assignees.
   * @param {FormGroup} form
   * @returns {ValidationErrors}
   */
  atLeastOneAssignee(form: UntypedFormGroup): ValidationErrors {
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
    if (index > 0 && this.assignedUsers.at(index - 1)) {
      const previousDeadline = this.assignedUsers.at(index - 1).get('deadline').value ? this.assignedUsers.at(index - 1).get('deadline').value : today;
      const dayAfterDeadline = new Date(previousDeadline);
      dayAfterDeadline.setDate(new Date(previousDeadline).getDate() + 1);
      return dayAfterDeadline;
    } else {
      return today
    }
  }

  /**
   * Check if property exists in current selected properties array.
   * @param {string} property
   * @returns {boolean}
   */
  isInSelectedProperties(property) {
    return this.selectedProperties.some(prop => prop === property);
  }

  //
  // Events.
  //

  /**
   * When paginator fires
   * @param uuid
   * @param page
   */
  onPageSelect(page) {
    this.page = page.pageIndex + 1;
    this.fetchDocuments(this.page, this.sortValue);
  }

  /**
   * When table is sorted
   * @param sortValue
   */
  sortTable(sortValue) {
    this.paginator.firstPage();
    this.page = 1;
    this.sortValue = sortValue;
    this.fetchDocuments(this.page, this.sortValue);
  }

  /**
   * On checkbox / doc select
   * @param event
   */
  onDocSelect(event) {
    this.selectedDocuments = event;
  }

  /**
   * Update selected properties array.
   * @param {MatCheckboxChange} event
   */
  updateSelectedProperties(event: MatCheckboxChange) {
    const selectedValue = event.source.value;
    const isInSelectedProperties = this.isInSelectedProperties(selectedValue);
    if (event.checked && !isInSelectedProperties) {
      this.selectedProperties.push(selectedValue)
    } else if (!event.checked && isInSelectedProperties) {
      const i = this.selectedProperties.findIndex(property => property === selectedValue);
      this.selectedProperties.splice(i, 1);
    }
  }

  /**
   * Adds a step to the form.
   * @param i
   */
  addStep(i, isPreconfig?) {
    if (this.extraStepControl(i)?.value || isPreconfig) {
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
   * Searches for users.
   */
  searchUsers(searchInput) {
    if (searchInput) {
      this.ketenProcessenService.getAccounts(searchInput).subscribe(res => {
        this.searchResultUsers = res.results;
      }, error => {
        this.errorMessage = error.error.detail ? error.error.detail : "Er is een fout opgetreden";
        this.reportError(error);
      })
    } else {
      this.searchResultUsers = [];
    }
  }

  /**
   * Searches for user groups.
   */
  searchUserGroups(searchInput) {
    if (searchInput) {
      this.ketenProcessenService.getUserGroups(searchInput).subscribe(res => {
        this.searchResultUserGroups = res.results;
      }, error => {
        this.errorMessage = error.error.detail ? error.error.detail : "Er is een fout opgetreden";
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
      documents: this.selectedDocuments,
      zaakeigenschappen: this.selectedProperties,
      toelichting: toelichting,
      id: this.taskContextData.context.previouslyAssignedUsers.length > 0 ? this.taskContextData.context.id : null
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
