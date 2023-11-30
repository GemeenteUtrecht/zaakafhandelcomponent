import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WorkstackCasesComponent } from './workstack-cases.component';

describe('WorkstackCasesComponent', () => {
  let component: WorkstackCasesComponent;
  let fixture: ComponentFixture<WorkstackCasesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ WorkstackCasesComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(WorkstackCasesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
