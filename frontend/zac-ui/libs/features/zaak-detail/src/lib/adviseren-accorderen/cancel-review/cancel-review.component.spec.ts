import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CancelReviewComponent } from './cancel-review.component';

describe('CancelReviewComponent', () => {
  let component: CancelReviewComponent;
  let fixture: ComponentFixture<CancelReviewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ CancelReviewComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(CancelReviewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
