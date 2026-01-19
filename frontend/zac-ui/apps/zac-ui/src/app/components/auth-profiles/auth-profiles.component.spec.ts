import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AuthProfilesComponent } from './auth-profiles.component';

describe('AuthProfilesComponent', () => {
  let component: AuthProfilesComponent;
  let fixture: ComponentFixture<AuthProfilesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AuthProfilesComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AuthProfilesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
