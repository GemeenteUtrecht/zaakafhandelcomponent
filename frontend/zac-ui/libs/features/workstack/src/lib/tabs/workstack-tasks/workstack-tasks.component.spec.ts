import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WorkstackTasksComponent } from './workstack-tasks.component';

describe('WorkstackTasksComponent', () => {
  let component: WorkstackTasksComponent;
  let fixture: ComponentFixture<WorkstackTasksComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ WorkstackTasksComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(WorkstackTasksComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
