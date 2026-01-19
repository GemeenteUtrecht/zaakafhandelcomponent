import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WorkstackReviewRequestsComponent } from './workstack-review-requests.component';

describe('WorkstackReviewRequestsComponent', () => {
  let component: WorkstackReviewRequestsComponent;
  let fixture: ComponentFixture<WorkstackReviewRequestsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ WorkstackReviewRequestsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(WorkstackReviewRequestsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
