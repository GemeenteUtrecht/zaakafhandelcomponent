import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DocumentsStepComponent } from './documents-step.component';

describe('DocumentsStepComponent', () => {
  let component: DocumentsStepComponent;
  let fixture: ComponentFixture<DocumentsStepComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DocumentsStepComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DocumentsStepComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
