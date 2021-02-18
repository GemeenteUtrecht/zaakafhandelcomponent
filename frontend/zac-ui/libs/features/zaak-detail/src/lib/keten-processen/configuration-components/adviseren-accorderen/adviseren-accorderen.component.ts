import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { DatePipe } from '@angular/common';
import { TaskContextData } from '../../../../models/task-context';
import { ApplicationHttpClient } from '@gu/services';
import { Result } from '../../../../models/user-search';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { KetenProcessenService } from '../../keten-processen.service';
import { atleastOneValidator, childValidator } from '@gu/utils';

@Component({
  selector: 'gu-config-adviseren-accorderen',
  templateUrl: './adviseren-accorderen.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class AdviserenAccorderenComponent implements OnChanges {
  @Input() taskContextData: TaskContextData;

  reviewType: 'advice' | 'approval';
  assignedUsersTitle = {
    advice: 'Adviseur(s)',
    approval: 'Accordeur(s)'
  }

  steps = 1;
  minDate = new Date();
  items: Result[] = [];

  // Form
  assignUsersForm: FormGroup;

  constructor(
    private http: ApplicationHttpClient,
    private fb: FormBuilder,
    private ketenProcessenService: KetenProcessenService,
    private datePipe: DatePipe
  ) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
      this.reviewType = this.taskContextData.context.reviewType;
      this.assignUsersForm = this.fb.group({
        documents: this.addDocumentCheckboxes(),
        assignedUsers: this.fb.array([this.addAssignUsersStep()]),
        toelichting: this.fb.control("")
      }, Validators.required)
    }
  }

  addStep() {
    this.steps++
    this.assignedUsers.push(this.addAssignUsersStep());
  }

  deleteStep(index) {
    this.steps--
    document.querySelector(`#configuration-multiselect--${index}`).remove();
    this.assignedUsers.removeAt(this.assignedUsers.length - 1);
  }

  addDocumentCheckboxes() {
    const arr = this.taskContextData.context.documents.map(() => {
      return this.fb.control(false);
    });
    return this.fb.array(arr, atleastOneValidator());
  }

  addAssignUsersStep() {
    const formGroup = this.fb.group({
      deadline: this.fb.control(null, Validators.required),
      users: this.fb.control([], Validators.minLength(1))
    }, childValidator())
    return this.fb.control(formGroup);
  }

  get documents(): FormArray {
    return this.assignUsersForm.controls.documents as FormArray;
  };

  get assignedUsers(): FormArray {
    return this.assignUsersForm.controls.assignedUsers as FormArray;
  };

  get toelichting(): FormControl {
    return this.assignUsersForm.controls.toelichting as FormControl;
  };

  onSearch(searchInput) {
    this.ketenProcessenService.getAccounts(searchInput).subscribe(res => {
      this.items = res.results;
    })
  }

  submitForm() {
    const selectedDocuments = this.documents.value
      .map((checked, i) => checked ? this.taskContextData.context.documents[i].url : null)
      .filter(v => v !== null);
    const assignedUsers = this.assignedUsers.controls
      .map( step => {
        const deadline = this.datePipe.transform(step.value.controls['deadline'].value, "yyyy-MM-dd");
        return {
          deadline: deadline,
          users: step.value.controls['users'].value
        }
      })
    const toelichting = this.toelichting.value;
    const formData = {
      form: this.taskContextData.form,
      assignedUsers: assignedUsers,
      selectedDocuments: selectedDocuments,
      toelichting: toelichting
    };
    this.putForm(formData);
  }

  putForm(formData) {
    this.ketenProcessenService.putTaskData(this.taskContextData.task.id, formData).subscribe(() => {
    })
  }
}
