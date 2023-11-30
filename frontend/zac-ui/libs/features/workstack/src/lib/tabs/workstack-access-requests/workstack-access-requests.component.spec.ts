import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WorkstackAccessRequestsComponent } from './workstack-access-requests.component';

describe('WorkstackAccessRequestsComponent', () => {
  let component: WorkstackAccessRequestsComponent;
  let fixture: ComponentFixture<WorkstackAccessRequestsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ WorkstackAccessRequestsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(WorkstackAccessRequestsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
