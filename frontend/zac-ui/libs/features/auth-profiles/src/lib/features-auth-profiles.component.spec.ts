import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FeaturesAuthProfilesComponent } from './features-auth-profiles.component';

describe('FeaturesAuthProfilesComponent', () => {
  let component: FeaturesAuthProfilesComponent;
  let fixture: ComponentFixture<FeaturesAuthProfilesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ FeaturesAuthProfilesComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(FeaturesAuthProfilesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
