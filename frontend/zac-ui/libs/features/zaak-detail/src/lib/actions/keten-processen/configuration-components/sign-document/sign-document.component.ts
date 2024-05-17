import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild } from '@angular/core';
import { TaskContextData } from '../../../../../models/task-context';
import { UntypedFormArray, UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import { ApplicationHttpClient, ZaakService } from '@gu/services';
import { KetenProcessenService } from '../../keten-processen.service';
import { Document, ListDocuments, RowData, Table, UserSearchResult, Zaak } from '@gu/models';
import { ModalService, PaginatorComponent } from '@gu/components';

@Component({
  selector: 'gu-sign-document',
  templateUrl: './sign-document.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class SignDocumentComponent implements OnChanges {
  @ViewChild(PaginatorComponent) paginator: PaginatorComponent;

  @Input() zaak: Zaak;
  @Input() taskContextData: TaskContextData;

  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  steps = 1;
  items: UserSearchResult[] = [];

  signDocumentForm: UntypedFormGroup;

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

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;

  constructor(
    private http: ApplicationHttpClient,
    private fb: UntypedFormBuilder,
    private ketenProcessenService: KetenProcessenService,
    private modalService: ModalService,
    private zaakService: ZaakService,
  ) { }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
      this.signDocumentForm = this.fb.group({
        assignedUsers: this.fb.array([this.addAssignUsersStep()]),
      })
      this.fetchDocuments();
    }
  }

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

  addStep() {
    this.steps++
    this.assignedUsers.push(this.addAssignUsersStep());
  }

  deleteStep() {
    this.steps--
    this.assignedUsers.removeAt(this.assignedUsers.length - 1);
  }

  onSearch(searchInput) {
    this.ketenProcessenService.getAccounts(searchInput).subscribe(res => {
      this.items = res.results;
    })
  }

  submitForm() {
    this.isSubmitting = true;

    const assignedUsers = this.assignedUsers.controls
      .map( (step, i) => {
        return {
          username: this.assignedUsersUsername(i).value,
          firstName: this.assignedUsersFirstname(i).value,
          lastName: this.assignedUsersLastname(i).value,
          email: this.assignedUsersEmail(i).value
        }
      })
    const formData = {
      form: this.taskContextData.form,
      assignedUsers: assignedUsers,
      selectedDocuments: this.selectedDocuments,
    };
    this.putForm(formData);
  }

  putForm(formData) {
    this.ketenProcessenService.putTaskData(this.taskContextData.task.id, formData).subscribe(() => {
      this.isSubmitting = false;
      this.submitSuccess = true;
      this.successReload.emit(true);

      this.modalService.close('ketenprocessenModal');
    }, res => {
      this.isSubmitting = false;
      this.submitErrorMessage = res.error.detail ? res.error.detail : "Er is een fout opgetreden";
      this.submitHasError = true;
    })
  }

  addAssignUsersStep() {
    return this.fb.group({
      username: ["", Validators.minLength(1)],
      firstName: ["", Validators.required],
      lastName: ["", Validators.required],
      email: ["", {validators: [Validators.email, Validators.required], updateOn: 'blur'}],
    })
  }

  get assignedUsers(): UntypedFormArray {
    return this.signDocumentForm.get('assignedUsers')  as UntypedFormArray;
  };

  assignedUsersUsername(index: number): UntypedFormControl {
    return this.assignedUsers.at(index).get('username') as UntypedFormControl;
  }

  assignedUsersFirstname(index: number): UntypedFormControl {
    return this.assignedUsers.at(index).get('firstName') as UntypedFormControl;
  }

  assignedUsersLastname(index: number): UntypedFormControl {
    return this.assignedUsers.at(index).get('lastName') as UntypedFormControl;
  }

  assignedUsersEmail(index: number): UntypedFormControl {
    return this.assignedUsers.at(index).get('email') as UntypedFormControl;
  }
}
