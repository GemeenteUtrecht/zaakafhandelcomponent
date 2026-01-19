import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DocumentToevoegenContezzaComponent } from './document-toevoegen-contezza.component';

describe('DocumentToevoegenContezzaComponent', () => {
  let component: DocumentToevoegenContezzaComponent;
  let fixture: ComponentFixture<DocumentToevoegenContezzaComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DocumentToevoegenContezzaComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DocumentToevoegenContezzaComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
