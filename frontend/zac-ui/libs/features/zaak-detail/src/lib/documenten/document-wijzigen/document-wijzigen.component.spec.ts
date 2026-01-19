import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DocumentWijzigenComponent } from './document-wijzigen.component';

describe('DocumentWijzigenComponent', () => {
  let component: DocumentWijzigenComponent;
  let fixture: ComponentFixture<DocumentWijzigenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DocumentWijzigenComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DocumentWijzigenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
