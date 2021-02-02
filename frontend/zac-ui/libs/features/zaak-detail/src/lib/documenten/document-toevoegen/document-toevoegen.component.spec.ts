import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DocumentToevoegenComponent } from './document-toevoegen.component';

describe('DocumentToevoegenComponent', () => {
  let component: DocumentToevoegenComponent;
  let fixture: ComponentFixture<DocumentToevoegenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DocumentToevoegenComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DocumentToevoegenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
