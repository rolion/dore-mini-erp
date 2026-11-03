import { importProvidersFrom } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { BehaviorSubject } from 'rxjs';
import { SigninComponent } from '../../authentication/signin/signin.component';
import { ORDER_STATUS_LABELS } from '../../features/sales/models/order';
import { ModuleDisabledComponent } from '../../features/settings/pages/module-disabled/module-disabled.component';
import { AuthService } from '../service/auth.service';
import { ModulesService } from '../service/modules.service';
import { provideTestTranslations } from './testing';

describe('screens in English and Portuguese (AC-03, AC-07, AC-08)', () => {
  async function use(lang: string): Promise<void> {
    await TestBed.inject(TranslateService).use(lang).toPromise();
  }

  it('renders the sign-in screen in English and Portuguese', async () => {
    TestBed.configureTestingModule({
      imports: [SigninComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        importProvidersFrom(FeatherModule.pick(allIcons)),
        { provide: AuthService, useValue: jasmine.createSpyObj<AuthService>('AuthService', ['login']) },
      ],
    });
    const fixture = TestBed.createComponent(SigninComponent);
    fixture.detectChanges();
    const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text()).toContain('Contraseña');
    await use('en');
    fixture.detectChanges();
    expect(text()).toContain('Password');
    expect(text()).not.toContain('Contraseña');
    await use('pt');
    fixture.detectChanges();
    expect(text()).toContain('Senha');
  });

  it('renders the module-disabled screen in English', async () => {
    TestBed.configureTestingModule({
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { queryParamMap: new BehaviorSubject(convertToParamMap({})) } },
        { provide: ModulesService, useValue: { enabledKeys$: new BehaviorSubject<ReadonlySet<string> | null>(new Set(['catalog'])), modules$: new BehaviorSubject([]) } },
      ],
    });
    const fixture = TestBed.createComponent(ModuleDisabledComponent);
    await use('en');
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Module not enabled');
  });

  it('labels coming from code follow the active language', async () => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations()] });
    expect(ORDER_STATUS_LABELS.DELIVERED).toBe('Entregado');
    await use('en');
    expect(ORDER_STATUS_LABELS.DELIVERED).toBe('Delivered');
    await use('pt');
    expect(ORDER_STATUS_LABELS.DELIVERED).toBe('Entregue');
  });
});
