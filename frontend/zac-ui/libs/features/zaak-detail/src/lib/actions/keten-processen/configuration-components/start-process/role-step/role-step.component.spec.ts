import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RoleStepComponent } from './role-step.component';

describe('RoleStepComponent', () => {
  let component: RoleStepComponent;
  let fixture: ComponentFixture<RoleStepComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ RoleStepComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(RoleStepComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
