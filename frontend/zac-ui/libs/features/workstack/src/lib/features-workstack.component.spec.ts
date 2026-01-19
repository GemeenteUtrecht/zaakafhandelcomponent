import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FeaturesWorkstackComponent } from './features-workstack.component';

describe('FeaturesWorkstackComponent', () => {
  let component: FeaturesWorkstackComponent;
  let fixture: ComponentFixture<FeaturesWorkstackComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ FeaturesWorkstackComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(FeaturesWorkstackComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
