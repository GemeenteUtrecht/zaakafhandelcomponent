import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
  ViewChild
} from '@angular/core';
import { TaskContextData } from '../../../../../models/task-context';
import { ApplicationHttpClient, ZaakService } from '@gu/services';
import { KetenProcessenService } from '../../keten-processen.service';
import {
  Document,
  InformatieObjectType,
  ListDocuments,
  ReadWriteDocument,
  RowData,
  Table, Zaak
} from '@gu/models';
import { Choice, ModalService, PaginatorComponent } from '@gu/components';

/**
 * <gu-document-select [taskContextData]="taskContextData"></gu-document-select>
 *
 * This is a configuration component for document select tasks.
 *
 * Requires taskContextData: TaskContextData input for the form layout.
 *
 * Emits successReload: boolean after successfully submitting the form.
 */
@Component({
  selector: 'gu-document-select',
  templateUrl: './document-select.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class DocumentSelectComponent implements OnChanges {
  @ViewChild(PaginatorComponent) paginator: PaginatorComponent;
  @Input() zaak: Zaak;
  @Input() taskContextData: TaskContextData;

  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  allData: Document[] = [];
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
  changedDocumentTypes = {}

  hasDocTypeError = false;
  docTypeErrorMessage: string;

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;

  fetchedPages = [];

  constructor(
    private http: ApplicationHttpClient,
    private ketenProcessenService: KetenProcessenService,
    private modalService: ModalService,
    private zaakService: ZaakService,
  ) { }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called when any data-bound property of a directive changes. Define an ngOnChanges() method
   * to handle the changes.
   */
  ngOnChanges(changes: SimpleChanges): void {
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
      this.fetchDocuments();
    }
  }

  //
  // Context.
  //

  fetchDocuments(page = 1, sortValue?) {
    this.zaakService.listTaskDocuments(this.taskContextData.context.documentsLink, page, sortValue).subscribe(data => {
      if (!this.fetchedPages.includes(page)) {
        this.fetchedPages.push(page)
        this.allData.push(...data.results)
      }
      this.tableData = this.formatTableData(data.results, this.tableHead, this.zaak, this.taskContextData.context.informatieobjecttypen, this.onConfidentialityChange.bind(this));
      this.paginatedDocsData = data;
      this.documentsData = data.results;
    })
  }

  /**
   * Create table
   * @param data
   * @param tableHead
   * @param {Zaak} zaak
   * @param {InformatieObjectType[]} informatieobjecttypen
   * @param {Function} onChange
   * @param {any[]} invalidTypes
   * @returns {Table}
   */
  formatTableData(data, tableHead, zaak: Zaak, informatieobjecttypen: InformatieObjectType[], onChange: Function, invalidTypes = []) {
    tableHead = [
      '',
      'Bestandsnaam',
      'Versie',
      'Auteur',
      'Informatieobjecttype',
    ]

    const tableData: Table = new Table(tableHead, []);
    tableData.bodyData = data.map((element: Document) => {
      let val;
      if (Object.keys(this.changedDocumentTypes).length > 0) {
        if (this.changedDocumentTypes.hasOwnProperty(element.url)) {
          val = this.changedDocumentTypes[element.url]['newValue'];
        } else {
          val = element.informatieobjecttype.url;
        }
      } else {
        val = element.informatieobjecttype.url;
      }
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
          informatieobjecttype: {
            choices: informatieobjecttypen.map(type => ({
              label: type.omschrijving,
              value: type.url
            })),
            type: 'select',
            value: val,
            onChange: (choice) => {onChange(element, choice)}
          },
        }
      }
      return cellData;
    })

    return tableData
  }


  /**
   * PUTs form data to API.
   * @param formData
   */
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

  /**
   * Open document
   * @param url
   */
  readDocument(url) {
    this.ketenProcessenService.readDocument(url).subscribe((res: ReadWriteDocument) => {
      window.open(res.magicUrl, "_blank");
    });
  }

  /**
   * Checks if objecttype exists in the context data
   * @param objecttype
   * @returns {InformatieObjectType}
   */
  findDocumentTypeObject(objecttype): InformatieObjectType {
    return this.taskContextData.context.informatieobjecttypen
      .filter(type => {
        return type.url === objecttype.url;
      })[0]
  }

  //
  // Events.
  //

  /**
   * When user selects a confidentiality
   * @param {Document} document
   * @param {Choice} confidentialityChoice
   */
  onConfidentialityChange(document: Document, confidentialityChoice: Choice) {
    if (this.changedDocumentTypes.hasOwnProperty(document.url)) {
      if (document.informatieobjecttype === confidentialityChoice.value) {
        delete this.changedDocumentTypes[document.url]
      } else {
        this.changedDocumentTypes[document.url]['newValue'] = confidentialityChoice.value;
      }
    } else {
      if (document.informatieobjecttype !== confidentialityChoice.value) {
        this.changedDocumentTypes[document.url] = {
          originalValue: document.informatieobjecttype,
          newValue: confidentialityChoice.value
        }
      }
    }
    this.hasDocTypeError = false;
  }

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
   * On checkbox / doc select
   * @param event
   */
  onDocSelect(event) {
    this.selectedDocuments = event;
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
   * Creates form data for request.
   */
  submitForm() {
    this.isSubmitting = true;
    this.hasDocTypeError = false;

    const invalidDocTypeUrls = [];

    const selectedDocs = this.selectedDocuments.map(d => {
      if (this.changedDocumentTypes.hasOwnProperty(d)) {
        return {
          document: d,
          documentType: this.changedDocumentTypes[d]['newValue']
        }
      } else {
        // Check if document type exists in list of informatieobject types
        const docType = this.allData.find(obj => obj['url'] === d).informatieobjecttype;
        const isValidDocType = this.findDocumentTypeObject(docType);
        if (!isValidDocType) {
          invalidDocTypeUrls.push(docType.url)
          this.hasDocTypeError = true;
          return null;
        }
        return {
          document: d,
          documentType: docType.url
        }
      }
    });

    const formData = {
      form: this.taskContextData.form,
      selectedDocuments: selectedDocs,
    };
    const invalids = invalidDocTypeUrls.map(url => {
      return this.allData.find(obj => obj['informatieobjecttype']['url'] === url).informatieobjecttype.omschrijving;
    })
    this.docTypeErrorMessage = "De volgende informatieobjecttypen bestaan niet: " + invalids.join(", ")

    if (!this.hasDocTypeError) {
      this.putForm(formData);
    } else {
      this.isSubmitting = false;
    }
  }


}
