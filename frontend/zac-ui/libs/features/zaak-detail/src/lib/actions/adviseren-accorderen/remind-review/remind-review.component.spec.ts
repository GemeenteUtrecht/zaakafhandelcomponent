import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RemindReviewComponent } from './remind-review.component';

describe('RemindReviewComponent', () => {
  let component: RemindReviewComponent;
  let fixture: ComponentFixture<RemindReviewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ RemindReviewComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(RemindReviewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
