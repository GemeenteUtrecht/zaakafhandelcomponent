import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DocumentenComponent } from './documenten.component';

describe('DocumentenComponent', () => {
  let component: DocumentenComponent;
  let fixture: ComponentFixture<DocumentenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DocumentenComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DocumentenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
