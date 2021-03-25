import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WorkstackComponent } from './workstack.component';

describe('WorkstackComponent', () => {
  let component: WorkstackComponent;
  let fixture: ComponentFixture<WorkstackComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ WorkstackComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(WorkstackComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
