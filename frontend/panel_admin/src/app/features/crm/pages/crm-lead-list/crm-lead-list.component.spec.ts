import { provideTestTranslations } from '../../../../core/i18n/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { ConvertLeadDialogComponent } from '../../components/convert-lead-dialog/convert-lead-dialog.component';
import { LeadDialogComponent } from '../../components/lead-dialog/lead-dialog.component';
import { CrmApiError } from '../../models/board';
import { CrmLead, CrmLeadPage } from '../../models/lead';
import { CrmLeadsApiService } from '../../services/crm-leads-api.service';
import { makeLead } from '../../testing/crm-fixtures';
import { CrmLeadListComponent } from './crm-lead-list.component';

describe('CrmLeadListComponent', () => {
  let fixture: ComponentFixture<CrmLeadListComponent>;
  let component: CrmLeadListComponent;
  let api: jasmine.SpyObj<CrmLeadsApiService>;
  let modal: jasmine.SpyObj<NgbModal>;
  let compact$: BehaviorSubject<{ matches: boolean }>;

  const carla = makeLead({ id: 'a', name: 'Carla Rojas' });
  const dani = makeLead({ id: 'b', name: 'Dani', phone: '', email: '', convertedCustomerId: 'c-9' });
  const page = (results: CrmLead[], count = results.length): CrmLeadPage => ({ count, results });

  async function setup(first: CrmLeadPage = page([carla, dani]), compact = false): Promise<void> {
    api = jasmine.createSpyObj<CrmLeadsApiService>('CrmLeadsApiService', ['list']);
    api.list.and.returnValue(of(first));
    modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    compact$ = new BehaviorSubject<{ matches: boolean }>({ matches: compact });
    await TestBed.configureTestingModule({
      imports: [CrmLeadListComponent],
      providers: [
        ...provideTestTranslations(), provideRouter([]),
        { provide: CrmLeadsApiService, useValue: api },
        { provide: NgbModal, useValue: modal },
        { provide: BreakpointObserver, useValue: { observe: () => compact$ } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(CrmLeadListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const query = (selector: string): HTMLElement | null => fixture.debugElement.query(By.css(selector))?.nativeElement ?? null;

  it('loads the first page and shows name, phone, email and status (AC-11)', async () => {
    await setup();
    expect(api.list).toHaveBeenCalledWith({ search: '', converted: undefined, page: 1, pageSize: 10 });
    expect(text()).toContain('Carla Rojas');
    expect(text()).toContain('carla@ejemplo.com');
    expect(text()).toContain('Nuevo');
    expect(query('[data-testid="converted-badge"]')?.getAttribute('href')).toContain('/pocketbiz/customers/c-9');
    // Solo los prospectos sin convertir ofrecen «Convertir en cliente».
    expect(fixture.debugElement.queryAll(By.css('[data-testid="convert-lead"]')).length).toBe(1);
  });

  it('searches after the debounce and filters by conversion status from page 1', fakeAsync(() => {
    setup().then(() => undefined);
    tick();
    fixture.detectChanges();
    api.list.calls.reset();
    component.searchControl.setValue('car');
    tick(300);
    expect(api.list).toHaveBeenCalledWith({ search: 'car', converted: undefined, page: 1, pageSize: 10 });
    component.convertedControl.setValue('false');
    expect(api.list).toHaveBeenCalledWith({ search: 'car', converted: false, page: 1, pageSize: 10 });
    component.convertedControl.setValue('true');
    expect(api.list).toHaveBeenCalledWith({ search: 'car', converted: true, page: 1, pageSize: 10 });
  }));

  it('requests another page', async () => {
    await setup(page([carla], 25));
    component.onPage({ offset: 1 });
    expect(api.list).toHaveBeenCalledWith({ search: '', converted: undefined, page: 2, pageSize: 10 });
  });

  it('shows the empty state with and without filters', async () => {
    await setup(page([]));
    expect(query('[data-testid="lead-empty"]')?.textContent).toContain('Aún no hay prospectos.');
    expect(query('[data-testid="empty-new"]')).not.toBeNull();
    component.searchControl.setValue('zzz', { emitEvent: false });
    component.applyFilters();
    fixture.detectChanges();
    expect(query('[data-testid="lead-empty"]')?.textContent).toContain('No hay prospectos que coincidan');
    query('[data-testid="empty-clear"]')?.click();
    expect(component.searchControl.value).toBe('');
  });

  it('shows an error with retry', async () => {
    await setup();
    api.list.and.returnValue(throwError(() => new CrmApiError('No se pudo conectar con el servidor.', 0)));
    component.retry();
    fixture.detectChanges();
    expect(query('[data-testid="lead-error"]')?.textContent).toContain('No se pudo conectar');
    api.list.and.returnValue(of(page([carla])));
    query('[data-testid="retry"]')?.click();
    fixture.detectChanges();
    expect(query('[data-testid="lead-error"]')).toBeNull();
  });

  it('creates and edits leads in the dialog and reloads with a confirmation', async () => {
    await setup();
    const instance = jasmine.createSpyObj<LeadDialogComponent>('dialog', ['edit']);
    modal.open.and.returnValue({ componentInstance: instance, result: Promise.resolve(makeLead({ name: 'Eva' })) } as never);
    query('[data-testid="new-lead"]')?.click();
    expect(modal.open).toHaveBeenCalledWith(LeadDialogComponent, jasmine.any(Object));
    await fixture.whenStable();
    fixture.detectChanges();
    expect(query('[data-testid="success"]')?.textContent).toContain('Prospecto «Eva» registrado.');
    query('[data-testid="edit-lead"]')?.click();
    expect(instance.edit).toHaveBeenCalledWith(carla);
  });

  it('converts a lead and reports whether the customer was created or linked (AC-11)', async () => {
    await setup();
    const instance = jasmine.createSpyObj<ConvertLeadDialogComponent>('dialog', ['open']);
    modal.open.and.returnValue({
      componentInstance: instance,
      result: Promise.resolve({ lead: carla, customer: { id: 'c-1', name: 'Carla Rojas', phone: '' }, created: false }),
    } as never);
    const calls = api.list.calls.count();
    query('[data-testid="convert-lead"]')?.click();
    expect(instance.open).toHaveBeenCalledOnceWith({ id: 'a', name: 'Carla Rojas', phone: '76543210' });
    await fixture.whenStable();
    fixture.detectChanges();
    expect(query('[data-testid="success"]')?.textContent).toContain('Se vinculó al cliente existente «Carla Rojas».');
    expect(api.list.calls.count()).toBe(calls + 1);
  });

  it('renders cards with collapsible filters on narrow screens (variante compacta)', async () => {
    await setup(page([carla, dani]), true);
    expect(fixture.debugElement.queryAll(By.css('[data-testid="lead-card"]')).length).toBe(2);
    expect(component.filtersCollapsed).toBeTrue();
    const calls = api.list.calls.count();
    component.searchControl.setValue('x');
    expect(api.list.calls.count()).toBe(calls); // en compacto no consulta hasta «Aplicar»
    component.applyFilters();
    expect(api.list.calls.count()).toBe(calls + 1);
    const edit = query('[data-testid="edit-lead"]');
    expect(edit?.getAttribute('aria-label')).toContain('Editar «Carla Rojas»');
    expect(edit?.getAttribute('title')).toBe('Editar');
  });
});
