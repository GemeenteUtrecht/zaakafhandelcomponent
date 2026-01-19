import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AbstractControl, UntypedFormBuilder, UntypedFormControl, UntypedFormGroup } from '@angular/forms';
import { AdviceService } from './advice.service';
import { AdviceForm } from '../../models/advice-form';
import {Requester, ReviewRequest} from '../../models/review-request';
import {DocumentUrls, ReadWriteDocument, RowData, Table, User, Zaak} from '@gu/models';
import { Review } from '../../models/review';
import { CloseDocument } from '../../models/close-document';
import { catchError, switchMap, tap } from 'rxjs/operators';
import { Observable, of } from 'rxjs';
import { AccountsService, UserService, ZaakService } from '@gu/services';
import { SnackbarService } from '@gu/components';
import { Document } from '@gu/models';

@Component({
  selector: 'gu-features-kownsl-advice',
  templateUrl: './advice.component.html',
  styleUrls: ['../features-kownsl.component.scss']
})
export class AdviceComponent implements OnInit {
  uuid: string;
  assignee: string;
  zaakUrl: string;
  bronorganisatie: string;
  requester: string;

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

  documentTableData: Table = new Table(['Bestandsnaam', 'Acties', ''], []);

  adviceForm: UntypedFormGroup;
  adviceFormData: AdviceForm = {
    advice: "",
    reviewDocuments: [],
    zaakeigenschappen: []
  };

  docsInEditMode: string[] = [];
  deleteUrls: DocumentUrls[] = [];


  get documents(): AbstractControl { return this.adviceForm.get('documents'); }

  constructor(
    private fb: UntypedFormBuilder,
    private adviceService: AdviceService,
    private accountsService: AccountsService,
    private route: ActivatedRoute,
    private userService: UserService,
    private zaakService: ZaakService,
    private snackbarService: SnackbarService,
  ) { }

  ngOnInit(): void {
    this.uuid = this.route.snapshot.queryParams["uuid"];
    this.assignee = this.route.snapshot.queryParams["assignee"];
    if (this.uuid && this.assignee) {
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
    this.adviceService.getAdvice(this.uuid, this.assignee)
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
          const { zaak } = res;
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
    this.setZaakUrl(res.zaak);
    this.bronorganisatie = res.zaak.bronorganisatie;
    this.adviceData = res;
    this.getStringifiedUser(this.adviceData.requester);
    this.tableData.bodyData = this.createTableData(res.advices);
    this.documentTableData.bodyData = this.createDocumentTableData(res.zaakDocuments);
  }

  /**
   * Returns the stringified version of user.
   * @param {User} user
   * @return {string}
   */
  getStringifiedUser(user: User|Requester) {
    this.accountsService.getAccounts(user.username)
      .subscribe(res => {
        this.requester = this.userService.stringifyUser(res.results[0] as User)
      }, err => {
        this.requester = this.userService.stringifyUser(user as User);
      })
  }

  getZaakDetails(bronorganisatie: string, identificatie: string): Observable<Zaak> {
    return this.zaakService.retrieveCaseDetails(bronorganisatie, identificatie)
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
      const rowData: RowData = {
        cellData: {
          author: author ? author : '',
          created: {
            type: review.created ? 'date' : 'text',
            date: review.created
          }
        },
        expandData: review.advice
      }
      return rowData
    });
  }

  // Document Edit

  createDocumentTableData(documents: Document[]): RowData[] {
    return documents.map( document => {
      const docName = document.bestandsnaam;
      const rowData: RowData = {
        cellData: {
          docName: docName,
          lezen: {
            type: 'button',
            label: 'Lezen',
            value: document.identificatie
          },
          bewerken: {
            type: 'button',
            label: 'Bewerken',
            value: document.identificatie
          }
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
    this.adviceService.readDocument(this.bronorganisatie, id, this.zaakData.url).subscribe( (res: ReadWriteDocument) => {
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
    this.adviceService.openDocumentEdit(this.bronorganisatie, id, this.zaakData.url).subscribe( (res: ReadWriteDocument) => {
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
    this.adviceFormData.zaakeigenschappen = this.adviceData.zaakeigenschappen.map(eigenschap => {
      return {
        url: eigenschap.url,
        naam: eigenschap.eigenschap.naam,
        waarde: eigenschap.waarde,
      }
    })

    this.adviceService.closeDocumentEdit(this.deleteUrls)
      .pipe(
        switchMap( (closedDocs: CloseDocument[]) => {
          const allDocs = this.adviceData.zaakDocuments.map(({ identificatie, url, versie }) => ({ id: identificatie, document: `${url}?versie=${versie}` }));

          const uneditedDocs = allDocs.filter(({ id }) => !this.deleteUrls.some(doc => doc.id === id)).map(({ document }) => ({ document }));

          const closedReviewDocs = closedDocs.length > 0 ? closedDocs.map((doc, i) => ({ document: this.deleteUrls[i].drcUrl, editedDocument: doc.versionedUrl })) : [];

          this.adviceFormData.reviewDocuments = closedDocs.length > 0 ? [...uneditedDocs, ...closedReviewDocs] : uneditedDocs;

          return of(this.adviceFormData);
        }),
        catchError(res => {
          if (this.submitFailed) {
            this.errorMessage = res.error.detail ? res.error.detail : 'Er is een fout opgetreden';
            return of(null)
          }
        }),
        switchMap(() => {
          return this.adviceService.postAdvice(this.adviceFormData, this.uuid, this.assignee);
        })
      ).subscribe( () => {
      this.isSubmitting = false;
      this.submitSuccess = true;
    }, errorRes => {
      this.isSubmitting = false;
      this.errorMessage = "Er is een fout opgetreden bij het versturen van uw gegevens."
      this.reportError(errorRes)
    })
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

  get adviceControl(): UntypedFormControl {
    return this.adviceForm.get('advice') as UntypedFormControl;
  };
}
