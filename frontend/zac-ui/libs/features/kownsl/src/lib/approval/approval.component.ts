import { Component, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ReviewRequest } from '../../models/review-request';
import { ApprovalService } from './approval.service';
import { RowData, Table } from '@gu/models';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ApprovalForm } from '../../models/approval-form';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'gu-features-kownsl-approval',
  templateUrl: './approval.component.html',
  styleUrls: ['../features-kownsl.component.scss']
})
export class ApprovalComponent implements OnInit {
  uuid: string;

  approvalData: ReviewRequest;
  isLoading: boolean;

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitFailed: boolean;

  hasError: boolean;
  errorMessage: string;

  tableData: Table = {
    headData: [],
    bodyData: []
  }

  approvalForm: FormGroup;

  pipe = new DatePipe("nl-NL");

  constructor(
    private fb: FormBuilder,
    private approvalService: ApprovalService,
    private route: ActivatedRoute
  ) { }

  ngOnInit(): void {
    this.uuid = this.route.snapshot.queryParams["uuid"];
    if (this.uuid) {
      this.fetchApproval()
      this.approvalForm = this.fb.group({
        approved: this.fb.control("", Validators.required),
        toelichting: this.fb.control("")
      })
    } else {
      this.errorMessage = "Er is geen geldig zaaknummer gevonden..."
    }
  }

  fetchApproval(): void {
    this.isLoading = true;
    this.approvalService.getApproval(this.uuid).subscribe(res => {
      const isSubmittedBefore = res.headers.get('X-Kownsl-Submitted');
      if (isSubmittedBefore === "false") {
        this.approvalData = res.body;
        this.tableData = this.createTableData(res.body);
      } else {
        this.hasError = true;
        this.errorMessage = "U heeft deze aanvraag al beantwoord.";
      }
      this.isLoading = false;
    }, res => {
      this.errorMessage = res.error.detail;
      this.hasError = true;
      this.isLoading = false;
    })
  }

  createTableData(approvalData: ReviewRequest): Table {
    const tableData: Table = {
      headData: ['Accordeur', 'Gedaan op', 'Akkoord'],
      bodyData: []
    }

    // Add table body data
    tableData.bodyData = approvalData.reviews.map( review => {
      const author = `${review.author.firstName} ${review.author.lastName}`;
      const date = this.pipe.transform(review.created, 'short');
      const approved = review.approved ? 'Akkoord' : 'Niet Akkoord';
      const rowData: RowData = {
        cellData: {
          author: author,
          created: date,
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
