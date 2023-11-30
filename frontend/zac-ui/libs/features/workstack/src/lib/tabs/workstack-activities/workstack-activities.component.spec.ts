import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WorkstackActivitiesComponent } from './workstack-activities.component';

describe('WorkstackActivitiesComponent', () => {
  let component: WorkstackActivitiesComponent;
  let fixture: ComponentFixture<WorkstackActivitiesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ WorkstackActivitiesComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(WorkstackActivitiesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
