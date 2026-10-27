import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { BehaviorSubject } from 'rxjs';
import { ModulesService } from '../../core/service/modules.service';
import { IfModuleDirective } from './if-module.directive';

@Component({
  imports: [IfModuleDirective],
  template: `<p *appIfModule="'inventory'" data-testid="stock">Stock</p>`,
})
class HostComponent {}

describe('IfModuleDirective (AC-04)', () => {
  let keys$: BehaviorSubject<ReadonlySet<string> | null>;

  const render = () => {
    const fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    return fixture;
  };
  const shown = (fixture: ReturnType<typeof render>) =>
    (fixture.nativeElement as HTMLElement).querySelector('[data-testid="stock"]') !== null;

  beforeEach(() => {
    keys$ = new BehaviorSubject<ReadonlySet<string> | null>(null);
    TestBed.configureTestingModule({
      providers: [{ provide: ModulesService, useValue: { enabledKeys$: keys$.asObservable() } }],
    });
  });

  it('does not render while the modules are unknown', () => {
    expect(shown(render())).toBeFalse();
  });

  it('renders only when its module is enabled', () => {
    keys$.next(new Set(['catalog', 'inventory']));
    expect(shown(render())).toBeTrue();
  });

  it('stays hidden when the module is disabled', () => {
    keys$.next(new Set(['catalog']));
    expect(shown(render())).toBeFalse();
  });

  it('adds and removes its content when the module is toggled', () => {
    keys$.next(new Set(['catalog']));
    const fixture = render();
    keys$.next(new Set(['catalog', 'inventory']));
    fixture.detectChanges();
    expect(shown(fixture)).toBeTrue();
    keys$.next(new Set(['catalog']));
    fixture.detectChanges();
    expect(shown(fixture)).toBeFalse();
  });
});
