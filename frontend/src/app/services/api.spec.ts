import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ApiService } from './api';
import { environment } from '../../environments/environment';

describe('ApiService - Saved Queries', () => {
  let service: ApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ApiService]
    });
    service = TestBed.inject(ApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should call GET /saved-queries when getSavedQueries is called', () => {
    const mockResponse = { success: true, queries: [] };

    service.getSavedQueries().subscribe(res => {
      expect(res).toEqual(mockResponse);
    });

    const req = httpMock.expectOne(`${environment.apiUrl}/saved-queries`);
    expect(req.request.method).toBe('GET');
    req.flush(mockResponse);
  });

  it('should call POST /saved-queries when createSavedQuery is called', () => {
    const mockResponse = {
      success: true,
      query: { id: '1', name: 'Test', query_params: {}, is_default: false }
    };

    service.createSavedQuery('Test', { search: 'crypto' }).subscribe(res => {
      expect(res.success).toBe(true);
      expect(res.query.name).toBe('Test');
    });

    const req = httpMock.expectOne(`${environment.apiUrl}/saved-queries`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ name: 'Test', query_params: { search: 'crypto' }, is_default: false });
    req.flush(mockResponse);
  });

  it('should call PUT /saved-queries/:id when updateSavedQuery is called', () => {
    const mockResponse = {
      success: true,
      query: { id: '1', name: 'Updated', query_params: { search: 'ai' }, is_default: true }
    };

    service.updateSavedQuery('1', { name: 'Updated', is_default: true }).subscribe(res => {
      expect(res.success).toBe(true);
    });

    const req = httpMock.expectOne(`${environment.apiUrl}/saved-queries/1`);
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({ name: 'Updated', is_default: true });
    req.flush(mockResponse);
  });

  it('should call DELETE /saved-queries/:id when deleteSavedQuery is called', () => {
    const mockResponse = { success: true, message: 'Deleted' };

    service.deleteSavedQuery('1').subscribe(res => {
      expect(res.success).toBe(true);
    });

    const req = httpMock.expectOne(`${environment.apiUrl}/saved-queries/1`);
    expect(req.request.method).toBe('DELETE');
    req.flush(mockResponse);
  });
});

describe('ApiService - Advanced Filters', () => {
  let service: ApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ApiService]
    });
    service = TestBed.inject(ApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should pass min_price and max_price as query params', () => {
    const mockResponse = { success: true, count: 0, total_count: 0, has_more: false, auctions: [] };

    service.getAuctionsReport({ min_price: 10, max_price: 500 }).subscribe();

    const req = httpMock.expectOne(r => r.url.includes('/auctions/report'));
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('min_price')).toBe('10');
    expect(req.request.params.get('max_price')).toBe('500');
    req.flush(mockResponse);
  });

  it('should pass keyword as query param', () => {
    const mockResponse = { success: true, count: 0, total_count: 0, has_more: false, auctions: [] };

    service.getAuctionsReport({ keyword: 'crypto' }).subscribe();

    const req = httpMock.expectOne(r => r.url.includes('/auctions/report'));
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('keyword')).toBe('crypto');
    req.flush(mockResponse);
  });
});