import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AnalysisProgress } from './analysis-progress';

describe('AnalysisProgress', () => {
  let component: AnalysisProgress;
  let fixture: ComponentFixture<AnalysisProgress>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AnalysisProgress],
    }).compileComponents();

    fixture = TestBed.createComponent(AnalysisProgress);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
