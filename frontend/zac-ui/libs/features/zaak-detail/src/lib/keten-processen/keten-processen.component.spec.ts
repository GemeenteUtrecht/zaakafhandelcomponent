import { ComponentFixture, TestBed } from '@angular/core/testing';

import { KetenProcessenComponent } from './keten-processen.component';

describe('KetenProcessenComponent', () => {
  let component: KetenProcessenComponent;
  let fixture: ComponentFixture<KetenProcessenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ KetenProcessenComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(KetenProcessenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
