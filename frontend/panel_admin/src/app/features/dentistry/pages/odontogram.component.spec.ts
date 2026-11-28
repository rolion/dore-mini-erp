import { provideTestTranslations } from '../../../core/i18n/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { Subject, of, throwError } from 'rxjs';
import { PersonnelApiService } from '../../personnel/services/personnel-api.service';
import { Evaluation } from '../models/odontogram';
import { DentistryApiService } from '../services/dentistry-api.service';
import { OdontogramApiService } from '../services/odontogram-api.service';
import { makeCatalog, makeEvaluation } from '../testing/odontogram-fixtures';
import { makePatient } from '../testing/patient-fixtures';
import { OdontogramComponent } from './odontogram.component';

const page = (results: Evaluation[]) => ({ count: results.length, next: null, previous: null, results });

describe('OdontogramComponent', () => {
  let fixture: ComponentFixture<OdontogramComponent>;
  let api: jasmine.SpyObj<OdontogramApiService>;
  const root = () => fixture.nativeElement as HTMLElement;
  const component = () => fixture.componentInstance;
  const text = () => root().textContent ?? '';
  const body = (selector: string) => document.querySelector<HTMLButtonElement>(selector);
  const button = (label: string) => Array.from(root().querySelectorAll('button')).find(b => b.textContent?.trim().includes(label));
  const tooth = (piece: number) => root().querySelector<HTMLButtonElement>(`[data-piece="${piece}"]`) as HTMLButtonElement;
  const field = (id: string) => root().querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(`#${id}`) as HTMLInputElement;
  const type = (id: string, value: string) => { const el = field(id); el.value = value; el.dispatchEvent(new Event(el.tagName === 'SELECT' ? 'change' : 'input')); fixture.detectChanges(); };

  async function setup(list: Evaluation[], detail: Evaluation | null = list[0] ?? null, archived = false) {
    api = jasmine.createSpyObj<OdontogramApiService>('api', ['catalog', 'list', 'get', 'create', 'update', 'discard', 'confirm', 'amend']);
    api.catalog.and.returnValue(of(makeCatalog()));
    api.list.and.returnValue(of(page(list)));
    api.get.and.callFake(() => of(detail as Evaluation));
    const patients = jasmine.createSpyObj<DentistryApiService>('patients', ['get']);
    patients.get.and.returnValue(of(makePatient({ active: !archived })));
    const personnel = jasmine.createSpyObj<PersonnelApiService>('personnel', ['list']);
    personnel.list.and.returnValue(of({ count: 1, next: null, previous: null, results: [
      { id: 'p-1', name: 'Dra. Rojas', active: true, created_by: 1, updated_by: 1, created_at: '', updated_at: '' }] }));
    await TestBed.configureTestingModule({ imports: [OdontogramComponent], providers: [...provideTestTranslations(), provideRouter([]),
      { provide: OdontogramApiService, useValue: api }, { provide: DentistryApiService, useValue: patients },
      { provide: PersonnelApiService, useValue: personnel },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'c-1' }), queryParamMap: convertToParamMap({}) } } },
    ] }).compileComponents();
    fixture = TestBed.createComponent(OdontogramComponent); fixture.detectChanges(); await fixture.whenStable(); fixture.detectChanges();
  }
  afterEach(() => TestBed.inject(NgbModal).dismissAll());

  it('shows the loading state, then the empty state with the initial-evaluation action (AC-11)', async () => {
    const pending = new Subject<ReturnType<typeof makeCatalog>>();
    api = jasmine.createSpyObj<OdontogramApiService>('api', ['catalog', 'list', 'get']);
    api.catalog.and.returnValue(pending); api.list.and.returnValue(of(page([])));
    const patients = jasmine.createSpyObj<DentistryApiService>('patients', ['get']); patients.get.and.returnValue(of(makePatient()));
    const personnel = jasmine.createSpyObj<PersonnelApiService>('personnel', ['list']); personnel.list.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    await TestBed.configureTestingModule({ imports: [OdontogramComponent], providers: [...provideTestTranslations(), provideRouter([]),
      { provide: OdontogramApiService, useValue: api }, { provide: DentistryApiService, useValue: patients }, { provide: PersonnelApiService, useValue: personnel },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'c-1' }), queryParamMap: convertToParamMap({}) } } }] }).compileComponents();
    fixture = TestBed.createComponent(OdontogramComponent); fixture.detectChanges();
    expect(root().querySelector('[role="status"]')?.textContent).toContain('Cargando');
    pending.next(makeCatalog()); pending.complete(); fixture.detectChanges();
    expect(root().querySelector('[data-testid="empty"]')?.textContent).toContain('aún no tiene evaluaciones');
    expect(button('Registrar evaluación inicial')).toBeDefined();
  });

  it('shows an error with retry when loading fails', async () => {
    api = jasmine.createSpyObj<OdontogramApiService>('api', ['catalog', 'list']);
    api.catalog.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500 }))); api.list.and.returnValue(of(page([])));
    const patients = jasmine.createSpyObj<DentistryApiService>('patients', ['get']); patients.get.and.returnValue(of(makePatient()));
    const personnel = jasmine.createSpyObj<PersonnelApiService>('personnel', ['list']); personnel.list.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    await TestBed.configureTestingModule({ imports: [OdontogramComponent], providers: [...provideTestTranslations(), provideRouter([]),
      { provide: OdontogramApiService, useValue: api }, { provide: DentistryApiService, useValue: patients }, { provide: PersonnelApiService, useValue: personnel },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'c-1' }), queryParamMap: convertToParamMap({}) } } }] }).compileComponents();
    fixture = TestBed.createComponent(OdontogramComponent); fixture.detectChanges();
    expect(root().querySelector('[role="alert"]')?.textContent).toContain('No se pudo');
    expect(button('Reintentar')).toBeDefined();
  });

  it('distinguishes draft from confirmed with a text badge and server allowed_actions (AC-07)', async () => {
    await setup([makeEvaluation()]);
    expect(root().querySelector('[data-testid="status-badge"]')?.textContent).toContain('Borrador');
    expect(button('Guardar borrador')).toBeDefined(); expect(button('Confirmar evaluación')).toBeDefined(); expect(button('Corregir')).toBeUndefined();
    const confirmed = makeEvaluation({ status: 'confirmed', allowed_actions: ['amend'], confirmed_at: '2026-11-21T10:00:00Z', confirmed_by: { id: 1, name: 'admin' } });
    TestBed.resetTestingModule();
    await setup([confirmed]);
    expect(root().querySelector('[data-testid="status-badge"]')?.textContent).toContain('Confirmada');
    expect(button('Guardar borrador')).toBeUndefined(); expect(button('Corregir')).toBeDefined();
    expect(text()).toContain('solo lectura');
    expect(root().querySelector('#odo-dentition')?.hasAttribute('disabled')).toBeTrue();
  });

  it('shows the chart and an equivalent table with piece, surfaces, condition and notes (AC-01, AC-11)', async () => {
    const evaluation = makeEvaluation({ findings: [
      { piece: 54, surfaces: ['O'], condition: 'caries', diagnosis: 'Caries oclusal', notes: '' },
      { piece: 16, surfaces: [], condition: 'crown', diagnosis: '', notes: 'Metal-cerámica' }] });
    await setup([evaluation]);
    expect(tooth(54).textContent).toContain('CAR'); expect(tooth(16).textContent).toContain('COR');
    button('Tabla')?.click(); fixture.detectChanges();
    const rows = Array.from(root().querySelectorAll('[data-testid="findings-table"] tbody tr')).map(row => row.textContent ?? '');
    expect(rows.length).toBe(2);
    expect(rows[0]).toContain('16'); expect(rows[0]).toContain('Pieza completa'); expect(rows[0]).toContain('Permanente'); expect(rows[0]).toContain('Metal-cerámica');
    expect(rows[1]).toContain('54'); expect(rows[1]).toContain('Temporal'); expect(rows[1]).toContain('O · Oclusal'); expect(rows[1]).toContain('Caries oclusal');
  });

  it('shows the selected piece with its findings and "Sin evaluar" otherwise (AC-12)', async () => {
    await setup([makeEvaluation({ findings: [{ piece: 16, surfaces: ['O'], condition: 'caries', diagnosis: '', notes: '' }] })]);
    expect(text()).toContain('Selecciona una pieza');
    tooth(11).click(); fixture.detectChanges();
    expect(text()).toContain('Pieza 11 · Incisivo Permanente'); expect(root().querySelector('[data-testid="piece-empty"]')?.textContent).toContain('Sin evaluar');
    tooth(16).click(); fixture.detectChanges();
    expect(root().querySelector('[data-testid="piece-panel"]')?.textContent).toContain('Caries (O)');
  });

  it('adds a finding on a temporary and a permanent piece and saves the draft with the full payload (AC-01)', async () => {
    await setup([makeEvaluation()]);
    const saved = makeEvaluation();
    api.update.and.returnValue(of(saved));
    tooth(54).click(); fixture.detectChanges();
    type('odo-condition', 'caries'); root().querySelector<HTMLInputElement>('#odo-surface-O')?.click(); fixture.detectChanges();
    (root().querySelector('[data-testid="finding-form"]') as HTMLFormElement).dispatchEvent(new Event('submit')); fixture.detectChanges();
    tooth(16).click(); fixture.detectChanges();
    type('odo-condition', 'crown');
    expect(root().querySelector('fieldset')?.hasAttribute('disabled')).toBeTrue();
    (root().querySelector('[data-testid="finding-form"]') as HTMLFormElement).dispatchEvent(new Event('submit')); fixture.detectChanges();
    expect(root().querySelector('[data-testid="save-status"]')?.textContent).toContain('Cambios sin guardar');
    button('Guardar borrador')?.click(); fixture.detectChanges();
    const payload = api.update.calls.mostRecent().args[1];
    expect(api.update.calls.mostRecent().args[0]).toBe('e-1');
    expect(payload.findings.map(f => [f.piece, f.condition, f.surfaces])).toEqual([[54, 'caries', ['O']], [16, 'crown', []]]);
    expect(text()).toContain('Borrador guardado');
  });

  it('validates required surfaces, the "Otro" note and duplicates before adding (AC-10)', async () => {
    await setup([makeEvaluation()]);
    tooth(16).click(); fixture.detectChanges();
    const submit = () => { (root().querySelector('[data-testid="finding-form"]') as HTMLFormElement).dispatchEvent(new Event('submit')); fixture.detectChanges(); };
    type('odo-condition', 'caries'); submit();
    expect(text()).toContain('Selecciona al menos una superficie');
    type('odo-condition', 'other'); submit();
    expect(text()).toContain('La nota es obligatoria');
    type('odo-notes', 'Hipoplasia'); submit();
    expect(root().querySelector('[data-testid="piece-panel"]')?.textContent).toContain('Otro');
    type('odo-condition', 'other'); type('odo-notes', 'Otra'); submit();
    expect(text()).toContain('ya está registrada');
  });

  it('keeps what the user typed and shows server field errors when saving fails (no double submit)', async () => {
    await setup([makeEvaluation({ findings: [{ piece: 16, surfaces: [], condition: 'crown', diagnosis: '', notes: '' }] })]);
    const pending = new Subject<Evaluation>();
    api.update.and.returnValue(pending);
    tooth(11).click(); fixture.detectChanges();
    type('odo-condition', 'healthy');
    (root().querySelector('[data-testid="finding-form"]') as HTMLFormElement).dispatchEvent(new Event('submit')); fixture.detectChanges();
    button('Guardar borrador')?.click(); button('Guardar borrador')?.click(); fixture.detectChanges();
    expect(api.update).toHaveBeenCalledTimes(1);
    expect(button('Guardar borrador')?.disabled).toBeTrue();
    pending.error(new HttpErrorResponse({ status: 400, error: { findings: [{ piece: ['Pieza 19 inválida.'] }] } })); fixture.detectChanges();
    expect(root().querySelector('[data-testid="save-error"]')?.textContent).toContain('Pieza 19 inválida.');
    expect(root().querySelector('[data-testid="save-status"]')?.textContent).toContain('Tus cambios siguen aquí');
    expect(tooth(11).textContent).toContain('SAN');
    expect(button('Guardar borrador')?.disabled).toBeFalse();
  });

  it('confirms through a dialog that warns about immutability (AC-05, AC-07)', async () => {
    const evaluation = makeEvaluation({ findings: [{ piece: 16, surfaces: [], condition: 'crown', diagnosis: '', notes: '' }] });
    await setup([evaluation]);
    const confirmed = makeEvaluation({ status: 'confirmed', allowed_actions: ['amend'] });
    api.confirm.and.returnValue(of(confirmed));
    button('Confirmar evaluación')?.click(); fixture.detectChanges();
    expect(document.body.textContent).toContain('no se puede editar');
    expect(api.confirm).not.toHaveBeenCalled();
    body('[data-testid="confirm-accept"]')?.click(); await fixture.whenStable(); fixture.detectChanges();
    expect(api.confirm).toHaveBeenCalledOnceWith('e-1');
    expect(api.update).not.toHaveBeenCalled();
    expect(text()).toContain('Evaluación confirmada.');
    expect(button('Guardar borrador')).toBeUndefined();
  });

  it('requires a reason to amend a confirmed evaluation and opens the new draft (AC-06)', async () => {
    const confirmed = makeEvaluation({ status: 'confirmed', allowed_actions: ['amend'] });
    await setup([confirmed]);
    const draft = makeEvaluation({ id: 'e-2', sequence: 2, amends_id: 'e-1', amends_sequence: 1, amendment_reason: 'Pieza mal marcada' });
    api.amend.and.returnValue(of(draft));
    button('Corregir')?.click(); fixture.detectChanges();
    const accept = body('[data-testid="amend-accept"]') as HTMLButtonElement;
    expect(accept.disabled).toBeTrue();
    const area = document.querySelector<HTMLTextAreaElement>('#odo-reason') as HTMLTextAreaElement;
    area.value = '   '; area.dispatchEvent(new Event('input')); fixture.detectChanges();
    expect(accept.disabled).toBeTrue();
    area.value = ' Pieza mal marcada '; area.dispatchEvent(new Event('input')); fixture.detectChanges();
    expect(accept.disabled).toBeFalse();
    accept.click(); await fixture.whenStable(); fixture.detectChanges();
    expect(api.amend).toHaveBeenCalledOnceWith('e-1', 'Pieza mal marcada');
    expect(text()).toContain('Corrige a #1');
    expect(text()).toContain('Pieza mal marcada');
    expect(root().querySelector('[data-testid="status-badge"]')?.textContent).toContain('Borrador');
  });

  it('lets the user switch between versions and keeps both (AC-02)', async () => {
    const second = makeEvaluation({ id: 'e-2', sequence: 2, status: 'confirmed', allowed_actions: ['amend'],
      findings: [{ piece: 26, surfaces: [], condition: 'crown', diagnosis: '', notes: '' }] });
    const first = makeEvaluation({ status: 'confirmed', allowed_actions: [], replaced_by_id: 'e-2', replaced_by_sequence: 2,
      findings: [{ piece: 16, surfaces: ['O'], condition: 'caries', diagnosis: '', notes: '' }] });
    await setup([second, first], second);
    const options = Array.from(root().querySelectorAll('#odo-version option')).map(o => o.textContent ?? '');
    expect(options.length).toBe(2); expect(options[0]).toContain('#2'); expect(options[1]).toContain('#1');
    api.get.and.returnValue(of(first));
    type('odo-version', 'e-1');
    expect(api.get).toHaveBeenCalledWith('e-1');
    expect(tooth(16).textContent).toContain('CAR');
    expect(text()).toContain('Reemplazada por #2');
  });

  it('is read-only with an explanation when the profile is archived (AC-09)', async () => {
    await setup([makeEvaluation()], makeEvaluation(), true);
    expect(text()).toContain('Perfil archivado');
    expect(button('Guardar borrador')).toBeUndefined(); expect(button('Nueva evaluación')).toBeUndefined();
  });

  it('creates the first draft from the empty state and sends the chosen dentition', async () => {
    await setup([], null);
    button('Registrar evaluación inicial')?.click(); fixture.detectChanges();
    type('odo-dentition', 'mixed');
    const created = makeEvaluation({ id: 'e-9' });
    api.create.and.returnValue(of(created));
    button('Guardar borrador')?.click(); fixture.detectChanges();
    expect(api.create).toHaveBeenCalledOnceWith('c-1', jasmine.objectContaining({ dentition: 'mixed', professional_id: null }));
    expect(root().querySelector('[data-testid="status-badge"]')?.textContent).toContain('Borrador');
  });

  it('offers the professionals from Personnel and general findings apart from the pieces (AC-08)', async () => {
    await setup([makeEvaluation()]);
    expect(Array.from(root().querySelectorAll('#odo-professional option')).map(o => o.textContent)).toContain('Dra. Rojas');
    type('odo-general-diagnosis', 'Bruxismo'); type('odo-general-notes', 'Nocturno');
    button('Agregar hallazgo general')?.click();
    (root().querySelectorAll('form')[1] as HTMLFormElement).dispatchEvent(new Event('submit')); fixture.detectChanges();
    expect(root().querySelector('[data-testid="general-table"]')?.textContent).toContain('Bruxismo');
    expect(root().querySelectorAll('[data-testid="findings-table"]').length).toBe(0);
  });

  it('keeps the created draft on screen when confirming fails after creating it, so a retry confirms it (REV-02)', async () => {
    await setup([], null);
    button('Registrar evaluación inicial')?.click(); fixture.detectChanges();
    tooth(16).click(); fixture.detectChanges(); type('odo-condition', 'healthy');
    (root().querySelector('[data-testid="finding-form"]') as HTMLFormElement).dispatchEvent(new Event('submit')); fixture.detectChanges();
    const created = makeEvaluation({ id: 'e-9', sequence: 3, findings: [{ piece: 16, surfaces: [], condition: 'healthy', diagnosis: '', notes: '' }] });
    api.create.and.returnValue(of(created));
    api.confirm.and.returnValues(throwError(() => new HttpErrorResponse({ status: 409, error: { detail: 'Perfil archivado.' } })),
      of(makeEvaluation({ id: 'e-9', sequence: 3, status: 'confirmed', allowed_actions: ['amend'] })));
    button('Confirmar evaluación')?.click(); fixture.detectChanges();
    body('[data-testid="confirm-accept"]')?.click(); await fixture.whenStable(); fixture.detectChanges();
    expect(api.create).toHaveBeenCalledTimes(1);
    expect(component().isNew).toBeFalse(); expect(component().current?.id).toBe('e-9');
    expect(api.list).toHaveBeenCalledTimes(2);
    expect(root().querySelector('[data-testid="save-error"]')?.textContent).toContain('Perfil archivado.');
    expect(button('Guardar borrador')?.disabled).toBeFalse();
    button('Confirmar evaluación')?.click(); fixture.detectChanges();
    (Array.from(document.querySelectorAll<HTMLButtonElement>('[data-testid="confirm-accept"]')).pop())?.click(); await fixture.whenStable(); fixture.detectChanges();
    expect(api.create).toHaveBeenCalledTimes(1);
    expect(api.confirm).toHaveBeenCalledTimes(2);
    expect(api.confirm.calls.mostRecent().args).toEqual(['e-9']);
    expect(text()).toContain('Evaluación confirmada.');
  });

  it('marks the invalid fields, links their message and moves focus to the first one (REV-05)', async () => {
    await setup([makeEvaluation()]);
    tooth(16).click(); fixture.detectChanges();
    const submit = () => { (root().querySelector('[data-testid="finding-form"]') as HTMLFormElement).dispatchEvent(new Event('submit')); fixture.detectChanges(); };
    submit(); await fixture.whenStable();
    expect(field('odo-condition').getAttribute('aria-invalid')).toBe('true');
    expect(field('odo-condition').getAttribute('aria-describedby')).toBe('odo-finding-errors');
    expect(document.activeElement).toBe(field('odo-condition'));
    type('odo-condition', 'other'); submit(); await fixture.whenStable();
    expect(field('odo-notes').getAttribute('aria-invalid')).toBe('true');
    expect(field('odo-condition').getAttribute('aria-invalid')).toBeNull();
    expect(document.activeElement).toBe(field('odo-notes'));
    const general = root().querySelectorAll('form')[1] as HTMLFormElement;
    general.dispatchEvent(new Event('submit')); fixture.detectChanges(); await fixture.whenStable();
    expect(field('odo-general-diagnosis').getAttribute('aria-invalid')).toBe('true');
    expect(document.activeElement).toBe(field('odo-general-diagnosis'));
  });

  it('shows the date error, flags the date field and focuses it when saving with an empty clinical date (REV-05)', async () => {
    await setup([makeEvaluation()]);
    type('odo-date', ''); button('Guardar borrador')?.click(); fixture.detectChanges(); await fixture.whenStable(); fixture.detectChanges();
    expect(api.update).not.toHaveBeenCalled();
    expect(field('odo-date').getAttribute('aria-invalid')).toBe('true');
    expect(field('odo-date').getAttribute('aria-describedby')).toBe('odo-date-error');
    expect(root().querySelector('#odo-date-error')?.textContent).toContain('fecha clínica válida');
    expect(document.activeElement).toBe(field('odo-date'));
  });

  it('implements the tabs keyboard pattern with a roving tabindex (REV-05)', async () => {
    await setup([makeEvaluation()]);
    const chartTab = root().querySelector<HTMLButtonElement>('#odo-tab-chart') as HTMLButtonElement;
    const tableTab = root().querySelector<HTMLButtonElement>('#odo-tab-table') as HTMLButtonElement;
    expect(chartTab.getAttribute('tabindex')).toBe('0'); expect(tableTab.getAttribute('tabindex')).toBe('-1');
    chartTab.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true })); fixture.detectChanges(); await fixture.whenStable();
    expect(tableTab.getAttribute('aria-selected')).toBe('true'); expect(tableTab.getAttribute('tabindex')).toBe('0');
    expect(document.activeElement).toBe(tableTab);
    tableTab.dispatchEvent(new KeyboardEvent('keydown', { key: 'Home', bubbles: true })); fixture.detectChanges(); await fixture.whenStable();
    expect(chartTab.getAttribute('aria-selected')).toBe('true');
    chartTab.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true })); fixture.detectChanges();
    expect(tableTab.getAttribute('aria-selected')).toBe('true');
  });

  it('formats dates as dd/MM/yyyy and dd/MM/yyyy HH:mm and shows a stacked list for narrow screens (REV-06)', async () => {
    const evaluation = makeEvaluation({ clinical_date: '2026-11-05', created_at: '2026-11-05T14:30:00', findings: [
      { piece: 54, surfaces: ['O'], condition: 'caries', diagnosis: 'Caries oclusal', notes: '' }] });
    await setup([evaluation]);
    expect(field('odo-version').textContent).toContain('05/11/2026');
    expect(text()).toContain('05/11/2026 14:30');
    button('Tabla')?.click(); fixture.detectChanges();
    const stacked = root().querySelector('[data-testid="findings-stacked"]') as HTMLElement;
    expect(stacked.classList).toContain('d-lg-none');
    expect(stacked.textContent).toContain('54'); expect(stacked.textContent).toContain('O · Oclusal'); expect(stacked.textContent).toContain('Caries oclusal');
    expect(root().querySelector('[data-testid="findings-table"]')?.closest('.table-responsive')?.classList).toContain('d-none');
  });

  it('shows a semantic breadcrumb with links to the list and the patient file (REV-06)', async () => {
    await setup([makeEvaluation()]);
    const nav = root().querySelector('nav ol.breadcrumb') as HTMLElement;
    expect(nav.querySelector('li.active')?.getAttribute('aria-current')).toBe('page');
    expect(Array.from(nav.querySelectorAll('a')).map(a => a.getAttribute('href'))).toEqual(['/pocketbiz/dentistry/patients', '/pocketbiz/dentistry/patients/c-1']);
  });
});
