import {Component, OnInit} from '@angular/core';
import {ReviewRequest} from '../../models/review-request';
import {ApprovalService} from './approval.service';
import {RowData, Table, Zaak} from '@gu/models';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import {ApprovalForm} from '../../models/approval-form';
import {ActivatedRoute} from '@angular/router';
import {catchError, switchMap, tap} from 'rxjs/operators';
import {Observable, of} from 'rxjs';
import {ZaakService} from "@gu/services";
import { SnackbarService } from '@gu/components';

@Component({
  selector: 'gu-features-kownsl-approval',
  templateUrl: './approval.component.html',
  styleUrls: ['../features-kownsl.component.scss']
})
export class ApprovalComponent implements OnInit {
  uuid: string;
  assignee: string;
  zaakUrl: string;

  approvalData: ReviewRequest;
  zaakData: Zaak;
  isLoading: boolean;

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitFailed: boolean;

  hasError: boolean;
  zaakHasError: boolean;
  errorMessage: string;

  tableData: Table = new Table([], []);

  approvalForm: FormGroup;

  constructor(
    private fb: FormBuilder,
    private approvalService: ApprovalService,
    private route: ActivatedRoute,
    private zaakService: ZaakService,
    private snackbarService: SnackbarService,
  ) {
  }

  ngOnInit(): void {
    this.uuid = this.route.snapshot.queryParams["uuid"];
    this.assignee = this.route.snapshot.queryParams["assignee"];
    if (this.uuid && this.assignee) {
      this.fetchData()
      this.approvalForm = this.fb.group({
        approved: this.fb.control("", Validators.required),
        toelichting: this.fb.control("")
      })
    } else {
      this.errorMessage = "Er is geen geldig zaaknummer gevonden."
    }
  }

  fetchData(): void {
    this.isLoading = true;
    this.approvalService.getApproval(this.uuid, this.assignee)
      .pipe(
        tap(res => {
          this.setLayout(res);
        }),
        catchError(res => {
          this.errorMessage = res.error.detail ? res.error.detail : 'Er is een fout opgetreden';
          this.hasError = true;
          this.isLoading = false;
          return of(null)
        }),
        switchMap(res => {
          const {zaak} = res?.body;
          return this.getZaakDetails(zaak.bronorganisatie, zaak.identificatie)
        })
      )
      .subscribe(() => {
        this.isLoading = false;
      }, error => {
        this.isLoading = false;
      })
  }

  setLayout(res) {
    this.setZaakUrl(res.body.zaak);
    this.approvalData = res.body;
    this.tableData = this.createTableData(res.body);
    this.isLoading = false;
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

  createTableData(approvalData: ReviewRequest): Table {
    const tableData: Table = new Table(['Accordeur', 'Gedaan op', 'Akkoord'], []);

    // Add table body data
    tableData.bodyData = approvalData.reviews.map(review => {
      const author = `${review.author.firstName} ${review.author.lastName}`;
      const approved = review.approved ? 'Akkoord' : 'Niet Akkoord';
      const rowData: RowData = {
        cellData: {
          author: author ? author : '',
          created: {
            type: review.created ? 'date' : 'text',
            date: review.created
          },
          approved: approved
        },
        expandData: review.toelichting
      }
      return rowData
    });

    return tableData;
  }

  submitForm(): void {
    const formData: ApprovalForm = {
      approved: this.approvalForm.controls['approved'].value,
      toelichting: this.approvalForm.controls['toelichting'].value
    }
    this.postApproval(formData);
  }

  postApproval(formData: ApprovalForm): void {
    this.isSubmitting = true;
    this.approvalService.postApproval(formData, this.uuid, this.assignee).subscribe(data => {
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

  get toelichtingControl(): FormControl {
    return this.approvalForm.get('toelichting') as FormControl;
  };
}
