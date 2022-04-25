import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DocumentSelectComponent } from './document-select.component';

describe('DocumentSelectComponent', () => {
  let component: DocumentSelectComponent;
  let fixture: ComponentFixture<DocumentSelectComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DocumentSelectComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DocumentSelectComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
