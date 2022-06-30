import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PropertiesStepComponent } from './properties-step.component';

describe('PropertiesStepComponent', () => {
  let component: PropertiesStepComponent;
  let fixture: ComponentFixture<PropertiesStepComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ PropertiesStepComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(PropertiesStepComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
