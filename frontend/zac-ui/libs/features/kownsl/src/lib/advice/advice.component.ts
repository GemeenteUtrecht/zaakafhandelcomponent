import { Component, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { AbstractControl, FormBuilder, FormGroup } from '@angular/forms';
import { AdviceService } from './advice.service';
import { AdviceForm } from '../../models/advice-form';
import { ReviewRequest } from '../../models/review-request';
import { RowData, Table, Zaak } from '@gu/models';
import { Review } from '../../models/review';
import { ZaakDocument } from '../../models/zaak-document';
import { DocumentUrls, ReadWriteDocument } from '../../../../zaak-detail/src/lib/documenten/documenten.interface';
import { CloseDocument } from '../../models/close-document';
import { catchError, switchMap, tap } from 'rxjs/operators';
import { Observable, of } from 'rxjs';

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
  zaakData: Zaak;
  isLoading: boolean;

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitFailed: boolean;

  hasError: boolean;
  zaakHasError: boolean;
  errorMessage: string;

  tableData: Table = new Table(['Adviseur', 'Gedaan op'], []);

  documentTableData: Table = new Table(['Acties', '', 'Documentnaam'], []);

  pipe = new DatePipe("nl-NL");

  adviceForm: FormGroup;
  adviceFormData: AdviceForm = {
    advice: "",
    documents: []
  };

  docsInEditMode: string[] = [];
  deleteUrls: DocumentUrls[] = [];


  get documents(): AbstractControl { return this.adviceForm.get('documents'); }

  constructor(
    private fb: FormBuilder,
    private adviceService: AdviceService,
    private route: ActivatedRoute,
  ) { }

  ngOnInit(): void {
    this.uuid = this.route.snapshot.queryParams["uuid"];
    if (this.uuid) {
      this.fetchData()
      this.adviceForm = this.fb.group({
        advice: this.fb.control(""),
      })
    } else {
      this.errorMessage = "Er is geen geldig zaaknummer gevonden."
    }
  }

  fetchData(): void {
    this.isLoading = true;
    this.adviceService.getAdvice(this.uuid)
      .pipe(
        tap( res => {
          this.setLayout(res);
        }),
        catchError(res => {
          this.errorMessage = res.error.detail ? res.error.detail : 'Er is een fout opgetreden';
          this.hasError = true;
          this.isLoading = false;
          return of(null)
        }),
        switchMap(res => {
          const { zaak } = res?.body;
          return this.getZaakDetails(zaak.bronorganisatie, zaak.identificatie)
        })
      )
      .subscribe( () => {
        this.isLoading = false;
      }, error => {
        this.isLoading = false;
      })
  }

  setLayout(res) {
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
  }

  getZaakDetails(bronorganisatie: string, identificatie: string): Observable<Zaak> {
    return this.adviceService.getZaakDetail(bronorganisatie, identificatie)
      .pipe(
        switchMap(zaak => {
          this.zaakData = zaak;
          return of(zaak);
        }),
        catchError(() => {
          this.zaakHasError = true;
          this.isLoading = false;
          return of(null);
        })
      );
  }

  setZaakUrl(zaakData: Zaak): void {
    this.zaakUrl = `/zaken/${zaakData.bronorganisatie}/${zaakData.identificatie}`;
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

  submitForm(): void {
    this.isSubmitting = true;


    this.adviceFormData.advice = this.adviceForm.controls['advice'].value;

    this.adviceService.closeDocumentEdit(this.deleteUrls)
      .pipe(
        switchMap( (closedDocs: CloseDocument[]) => {
          if (closedDocs.length > 0) {
            this.adviceFormData.documents = closedDocs.map( (doc, i) => {
              return {
                document: this.deleteUrls[i].drcUrl,
                editedDocument: doc.versionedUrl
              }
            })
          }
          return of(this.adviceFormData);
        }),
        catchError(res => {
          if (this.submitFailed) {
            this.errorMessage = res.error.detail ? res.error.detail : 'Er is een fout opgetreden';
            return of(null)
          }
        }),
        switchMap((formData: AdviceForm) => {
          return this.adviceService.postAdvice(this.adviceFormData, this.uuid)
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
