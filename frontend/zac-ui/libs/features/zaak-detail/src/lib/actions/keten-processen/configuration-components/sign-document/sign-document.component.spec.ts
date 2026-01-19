import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SignDocumentComponent } from './sign-document.component';

describe('SignDocumentComponent', () => {
  let component: SignDocumentComponent;
  let fixture: ComponentFixture<SignDocumentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SignDocumentComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(SignDocumentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
