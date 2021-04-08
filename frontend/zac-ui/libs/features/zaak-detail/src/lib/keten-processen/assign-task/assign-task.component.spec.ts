import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AssignTaskComponent } from './assign-task.component';

describe('AssignTaskComponent', () => {
  let component: AssignTaskComponent;
  let fixture: ComponentFixture<AssignTaskComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AssignTaskComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AssignTaskComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
