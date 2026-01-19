import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SetResultComponent } from './set-result.component';

describe('SetResultComponent', () => {
  let component: SetResultComponent;
  let fixture: ComponentFixture<SetResultComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SetResultComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(SetResultComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
