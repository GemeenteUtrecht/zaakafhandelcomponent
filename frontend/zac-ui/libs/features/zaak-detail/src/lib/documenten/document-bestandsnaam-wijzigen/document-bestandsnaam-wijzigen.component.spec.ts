import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DocumentBestandsnaamWijzigenComponent } from './document-bestandsnaam-wijzigen.component';

describe('DocumentBestandsnaamWijzigenComponent', () => {
  let component: DocumentBestandsnaamWijzigenComponent;
  let fixture: ComponentFixture<DocumentBestandsnaamWijzigenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DocumentBestandsnaamWijzigenComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DocumentBestandsnaamWijzigenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
