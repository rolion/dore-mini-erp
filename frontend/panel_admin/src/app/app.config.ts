import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig, importProvidersFrom } from '@angular/core';
import { APP_ROUTE } from './app.routes';
import { provideRouter } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { HashLocationStrategy, LocationStrategy } from '@angular/common';
import { tokenInterceptor } from '@core/interceptor/jwt.interceptor';
import { errorInterceptor } from '@core/interceptor/error.interceptor';
import { DirectionService, LanguageService } from '@core';
import { provideTranslateService } from '@ngx-translate/core';
import { provideTranslateHttpLoader } from '@ngx-translate/http-loader';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { provideCharts, withDefaultRegisterables } from 'ng2-charts';
import { provideToastr } from 'ngx-toastr';

export const appConfig: ApplicationConfig = {
    providers: [
        provideHttpClient(withInterceptors([tokenInterceptor, errorInterceptor])),
        provideRouter(APP_ROUTE),
        provideToastr(),
        provideAnimations(),
        { provide: LocationStrategy, useClass: HashLocationStrategy },
        DirectionService, LanguageService,
        provideTranslateService({
            defaultLanguage: 'es',
        }),
        provideTranslateHttpLoader({
            prefix: './assets/i18n/',
            suffix: '.json',
        }),
        importProvidersFrom(FeatherModule.pick(allIcons)),
        provideCharts(withDefaultRegisterables()),
    ],
};
