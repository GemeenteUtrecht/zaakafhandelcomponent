import { Component, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { AbstractControl, FormBuilder, FormGroup } from '@angular/forms';
import { AdviceService } from './advice.service';
import { AdviceForm, AdviceDocument } from '../../models/advice-form';
import { Zaak } from '../../models/zaak';
import { ReviewRequest } from '../../models/review-request';
import { RowData, Table } from '@gu/models';
import { Review } from '../../models/review';
import { ZaakDocument } from '../../models/zaak-document';
import { DocumentUrls, ReadWriteDocument } from '../../../../zaak-detail/src/lib/documenten/documenten.interface';
import { CloseDocument } from '../../models/close-document';
import { switchMap } from 'rxjs/operators';
import { of } from 'rxjs';

@Component({
  selector: 'gu-features-kownsl-advice',
  templateUrl: './advice.component.html',
  styleUrls: ['../features-kownsl.component.scss']
})
export class AdviceComponent implements OnInit {
  uuid: string;
  zaakUrl: string;
  bronorganisatie: string;

  adviceData: ReviewRequest;
  isLoading: boolean;

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitFailed: boolean;

  hasError: boolean;
  errorMessage: string;

  isNotLoggedIn: boolean;
  readonly NOT_LOGGED_IN_MESSAGE = "Authenticatiegegevens zijn niet opgegeven.";

  loginUrl: string;

  tableData: Table = {
    headData: ['Adviseur', 'Gedaan op'],
    bodyData: []
  }
  documentTableData: Table = {
    headData: ['Acties', '', 'Documentnaam'],
    bodyData: []
  }

  pipe = new DatePipe("nl-NL");

  adviceForm: FormGroup;

  docsInEditMode: string[] = [];
  deleteUrls: DocumentUrls[] = [];


  get documents(): AbstractControl { return this.adviceForm.get('documents'); }

  constructor(
    private fb: FormBuilder,
    private adviceService: AdviceService,
    private route: ActivatedRoute,
    private router: Router
  ) { }

  ngOnInit(): void {
    this.uuid = this.route.snapshot.queryParams["uuid"];
    if (this.uuid) {
      this.fetchAdvice()
      this.adviceForm = this.fb.group({
        advice: this.fb.control(""),
      })
    } else {
      this.errorMessage = "Er is geen geldig zaaknummer gevonden."
    }
  }

  fetchAdvice(): void {
    this.isLoading = true;
    this.adviceService.getAdvice(this.uuid).subscribe(res => {
      this.setZaakUrl(res.body.zaak);
      this.bronorganisatie = res.body.zaak.bronorganisatie;
      const isSubmittedBefore = res.headers.get('X-Kownsl-Submitted');
      if (isSubmittedBefore === "false") {
        this.adviceData = res.body;
        this.tableData.bodyData = this.createTableData(res.body.reviews);
        this.documentTableData.bodyData = this.createDocumentTableData(res.body.zaakDocuments);
      } else {
        this.hasError = true;
        this.errorMessage = "U heeft deze aanvraag al beantwoord.";
      }
      this.isLoading = false;
    }, res => {
      this.errorMessage = res.error.detail;
      if (this.errorMessage === this.NOT_LOGGED_IN_MESSAGE) {
        this.setLoginUrl()
        this.isNotLoggedIn = true;
      }
      this.hasError = true;
      this.isLoading = false;
    })
  }

  setZaakUrl(zaakData: Zaak): void {
    this.zaakUrl = `/zaken/${zaakData.bronorganisatie}/${zaakData.identificatie}`;
  }

  setLoginUrl(): void {
    const currentPath = this.router.url;
    this.loginUrl = `/accounts/login/?next=/ui${currentPath}`;
  }

  createTableData(reviews: Review[]): RowData[] {

    // Add table body data
    return reviews.map( review => {
      const author = `${review.author.firstName} ${review.author.lastName}`;
      const date = this.pipe.transform(review.created, 'short');
      const rowData: RowData = {
        cellData: {
          author: author ? author : '',
          created: date
        },
        expandData: review.advice
      }
      return rowData
    });
  }

  // Document Edit

  createDocumentTableData(documents: ZaakDocument[]): RowData[] {

    return documents.map( document => {
      const docName = `${document.name} (${document.title})`;
      const rowData: RowData = {
        cellData: {
          lezen: {
            type: 'button',
            label: 'Lezen',
            value: document.identificatie
          },
          bewerken: {
            type: 'button',
            label: 'Bewerken',
            value: document.identificatie
          },
          docName: docName
        }
      }
      return rowData
    });
  }

  handleTableButtonOutput(action: object) {
    const actionType = Object.keys(action)[0];
    const id = action[actionType];

    switch (actionType) {
      case 'lezen':
        this.readDocument(id);
        break;
      case 'bewerken':
        this.editDocument(id);
        break;
    }
  }

  readDocument(id) {
    this.adviceService.readDocument(this.bronorganisatie, id).subscribe( (res: ReadWriteDocument) => {
      window.open(res.magicUrl, "_blank");
    }, errorResponse => {

    })
  }

  editDocument(id) {
    if (!this.docsInEditMode.includes(id)) {
      this.docsInEditMode.push(id);
    }
    this.openDocumentEdit(id);
  }

  openDocumentEdit(id) {
    this.adviceService.openDocumentEdit(this.bronorganisatie, id).subscribe( (res: ReadWriteDocument) => {
      // Open document
      window.open(res.magicUrl, "_blank");

      // Map received deleteUrl to the id
      this.addDeleteUrlsMapping(id, res.deleteUrl, res.drcUrl);
    }, errorResponse => {

    })
  }

  addDeleteUrlsMapping(id, deleteUrl, drcUrl) {
    // Check if mapping already exists
    this.deleteUrls = this.deleteUrls.filter( item => item.id !== id)
    const urlMapping = {
      id: id,
      deleteUrl: deleteUrl,
      drcUrl: drcUrl
    }
    this.deleteUrls.push(urlMapping);
  }

  // submit
  submitForm(): void {
    this.isSubmitting = true;

    let adviceFormData: AdviceForm;
    const documentsData: Array<AdviceDocument> = [];

    adviceFormData = {
      advice: this.adviceForm.controls['advice'].value,
      documents: documentsData
    }

    this.adviceService.closeDocumentEdit(this.deleteUrls)
      .pipe(
        switchMap( (closedDocs: CloseDocument[]) => {
          adviceFormData.documents = closedDocs.map( (doc, i) => {
            return {
              document: this.deleteUrls[i].drcUrl,
              editedDocument: doc.versionedUrl
            }
          })
          return of(adviceFormData);
        }),
        switchMap((formData: AdviceForm) => {
          return this.adviceService.postAdvice(formData, this.uuid)
        })
      ).subscribe( () => {
      this.isSubmitting = false;
      this.submitSuccess = true;
    }, errorRes => {
      this.errorMessage = "Er is een fout opgetreden bij het verzenden van uw gegevens."
      this.submitFailed = true;
      this.isSubmitting = false;
    })

  }
}
