import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DocumentVertrouwelijkheidWijzigenComponent } from './document-vertrouwelijkheid-wijzigen.component';

describe('DocumentVertrouwelijkheidWijzigenComponent', () => {
  let component: DocumentVertrouwelijkheidWijzigenComponent;
  let fixture: ComponentFixture<DocumentVertrouwelijkheidWijzigenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DocumentVertrouwelijkheidWijzigenComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DocumentVertrouwelijkheidWijzigenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
