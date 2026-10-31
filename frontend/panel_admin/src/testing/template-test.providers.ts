import { EnvironmentProviders, importProvidersFrom, makeEnvironmentProviders } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { provideToastr } from 'ngx-toastr';
import { provideCharts, withDefaultRegisterables } from 'ng2-charts';

/** Application-level dependencies required by the inherited template smoke tests. */
export function provideTemplateTestServices(): EnvironmentProviders {
  return makeEnvironmentProviders([
    provideRouter([]),
    provideNoopAnimations(),
    provideToastr(),
    provideCharts(withDefaultRegisterables()),
    importProvidersFrom(FeatherModule.pick(allIcons)),
  ]);
}