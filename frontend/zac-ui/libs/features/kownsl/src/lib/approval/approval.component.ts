import { Component, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ReviewRequest } from '../../models/review-request';
import { ApprovalService } from './approval.service';
import { RowData, Table, Zaak } from '@gu/models';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ApprovalForm } from '../../models/approval-form';
import { ActivatedRoute, Router } from '@angular/router';
import { catchError, switchMap, tap } from 'rxjs/operators';
import { Observable, of } from 'rxjs';

@Component({
  selector: 'gu-features-kownsl-approval',
  templateUrl: './approval.component.html',
  styleUrls: ['../features-kownsl.component.scss']
})
export class ApprovalComponent implements OnInit {
  uuid: string;
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

  tableData: Table = new Table ([], []);

  approvalForm: FormGroup;

  pipe = new DatePipe("nl-NL");

  constructor(
    private fb: FormBuilder,
    private approvalService: ApprovalService,
    private route: ActivatedRoute,
    private router: Router
  ) { }

  ngOnInit(): void {
    this.uuid = this.route.snapshot.queryParams["uuid"];
    if (this.uuid) {
      this.fetchData()
      this.approvalForm = this.fb.group({
        approved: this.fb.control("", Validators.required),
        toelichting: this.fb.control("")
      })
    } else {
      this.errorMessage = "Er is geen geldig zaaknummer gevonden..."
    }
  }

  fetchData(): void {
    this.isLoading = true;
    this.approvalService.getApproval(this.uuid)
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
    const isSubmittedBefore = res.headers.get('X-Kownsl-Submitted');
    if (isSubmittedBefore === "false") {
      this.approvalData = res.body;
      this.tableData = this.createTableData(res.body);
    } else {
      this.hasError = true;
      this.errorMessage = "U heeft deze aanvraag al beantwoord.";
    }
    this.isLoading = false;
  }

  getZaakDetails(bronorganisatie: string, identificatie: string): Observable<Zaak> {
    return this.approvalService.getZaakDetail(bronorganisatie, identificatie)
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
    tableData.bodyData = approvalData.reviews.map( review => {
      const author = `${review.author.firstName} ${review.author.lastName}`;
      const date = this.pipe.transform(review.created, 'short');
      const approved = review.approved ? 'Akkoord' : 'Niet Akkoord';
      const rowData: RowData = {
        cellData: {
          author: author ? author : '',
          created: date ? date : '',
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
    this.approvalService.postApproval(formData, this.uuid).subscribe(data => {
      this.isSubmitting = false;
      this.submitSuccess = true;
    }, error => {
      this.errorMessage = "Er is een fout opgetreden bij het verzenden van uw gegevens..."
      this.submitFailed = true;
      this.isSubmitting = false;
    })
  }
}
