import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';

import { PurchaseApiError } from '../../models/purchase';
import { PurchasesApiService } from '../../services/purchases-api.service';
import { makePurchase } from '../../testing/purchase-fixtures';
import { PurchaseDetailComponent } from './purchase-detail.component';

describe('PurchaseDetailComponent', () => {
  let fixture: ComponentFixture<PurchaseDetailComponent>;
  let api: jasmine.SpyObj<PurchasesApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let router: Router;

  async function setup(purchase: ReturnType<typeof makePurchase> | PurchaseApiError): Promise<void> {
    api = jasmine.createSpyObj<PurchasesApiService>('PurchasesApiService', ['get']);
    api.get.and.returnValue(purchase instanceof PurchaseApiError ? throwError(() => purchase) : of(purchase));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [PurchaseDetailComponent],
      providers: [
        provideRouter([]),
        { provide: PurchasesApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'c-1' }) } } },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(PurchaseDetailComponent);
    fixture.detectChanges();
  }

  const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const hrefs = (): (string | null)[] =>
    fixture.debugElement.queryAll(By.css('a')).map((a) => (a.nativeElement as HTMLAnchorElement).getAttribute('href'));

  it('shows the header, the lines with their snapshot and the total (AC-17)', async () => {
    await setup(makePurchase());
    expect(api.get).toHaveBeenCalledWith('c-1');
    for (const expected of ['Distribuidora Sur', '29/10/2026', 'F-100', 'Entrega el martes', 'Borrador', 'BOB', 'Harina', 'kg', '2.500', 'Bs 10.00', 'Bs 25.00']) {
      expect(text()).withContext(expected).toContain(expected);
    }
    expect(fixture.debugElement.queryAll(By.css('[data-testid="item"]')).length).toBe(1);
  });

  it('offers Edit for a draft and does not offer Confirm yet (AC-17)', async () => {
    await setup(makePurchase());
    expect(hrefs()).toContain('/pocketbiz/purchases/c-1/edit');
    expect(text()).not.toContain('Confirmar');
  });

  it('hides Edit when the purchase is not editable (AC-17)', async () => {
    await setup(makePurchase({ editable: false }));
    expect(hrefs()).not.toContain('/pocketbiz/purchases/c-1/edit');
  });

  it('uses fallback texts and still shows an inactive supplier (AC-17)', async () => {
    await setup(makePurchase({ externalReference: '', notes: '', items: [], total: '0.00', supplier: { id: 's-1', name: 'Viejo', active: false } }));
    expect(text()).toContain('Sin referencia');
    expect(text()).toContain('Sin notas');
    expect(text()).toContain('Esta compra aún no tiene productos.');
    expect(text()).toContain('Viejo');
    expect(text()).toContain('Inactivo');
  });

  it('warns and returns to the list when the purchase does not exist (AC-17)', async () => {
    await setup(new PurchaseApiError('Compra no encontrada.', 404));
    expect(toastr.error).toHaveBeenCalledWith('Compra no encontrada.');
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases']);
  });
});
