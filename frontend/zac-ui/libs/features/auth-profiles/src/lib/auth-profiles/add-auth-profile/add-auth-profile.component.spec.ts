import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AddAuthProfileComponent } from './add-auth-profile.component';

describe('AddAuthProfileComponent', () => {
  let component: AddAuthProfileComponent;
  let fixture: ComponentFixture<AddAuthProfileComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AddAuthProfileComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AddAuthProfileComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
