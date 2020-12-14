import { Component, OnInit } from '@angular/core';
import { ReviewRequest } from '../../models/review-request';
import { ApprovalService } from './approval.service';
import { CellData, Table } from '@gu/models';
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
    elementData: []
  }

  approvalForm: FormGroup;

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
        approval: this.fb.control("", Validators.required),
        explanation: this.fb.control("")
      })
    } else {
      this.errorMessage = "Er is geen geldig zaaknummer gevonden..."
    }
  }

  fetchApproval(): void {
    this.isLoading = true;
    this.approvalService.getApproval(this.uuid).subscribe(data => {
      this.approvalData = data;
      this.createTableData(data);
      this.isLoading = false;
    }, error => {
      this.errorMessage = "Er is een fout opgetreden bij het ophalen van de details..."
      this.hasError = true;
      this.isLoading = false;
    })
  }

  createTableData(adviceData: ReviewRequest): void {
    // Add authors to table head
    this.tableData.headData = adviceData.reviews.map( review => {
      return review.author;
    });

    // Add table body data
    this.tableData.elementData = adviceData.reviews.map( review => {
      const cellData: CellData = {
        cellData: {
          author: review.author,
          created: review.created
        },
        expandData: review.toelichting
      }
      return cellData
    });
  }

  submitForm(): void {
    const formData: ApprovalForm = {
      approval: this.approvalForm.controls['approval'].value,
      explanation: this.approvalForm.controls['explanation'].value,
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
