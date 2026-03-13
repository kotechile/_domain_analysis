import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DomainAnalysis } from './domain-analysis';

describe('DomainAnalysis', () => {
  let component: DomainAnalysis;
  let fixture: ComponentFixture<DomainAnalysis>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DomainAnalysis],
    }).compileComponents();

    fixture = TestBed.createComponent(DomainAnalysis);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
