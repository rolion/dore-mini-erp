import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig, importProvidersFrom, inject, provideAppInitializer } from '@angular/core';
import { APP_ROUTE } from './app.routes';
import { provideRouter } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { tokenInterceptor } from '@core/interceptor/jwt.interceptor';
import { errorInterceptor } from '@core/interceptor/error.interceptor';
import { DirectionService, LanguageService } from '@core';
import { LANGUAGE_URL_SERIALIZER_PROVIDER } from '@core/i18n/language-url.serializer';
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
        DirectionService, LanguageService,
        LANGUAGE_URL_SERIALIZER_PROVIDER,
        provideTranslateService({
            fallbackLang: 'es',
            lang: 'es',
        }),
        // Carga el catálogo del idioma (URL > preferencia > español) antes del primer render.
        provideAppInitializer(() => inject(LanguageService).init()),
        provideTranslateHttpLoader({
            prefix: './assets/i18n/',
            suffix: '.json',
        }),
        importProvidersFrom(FeatherModule.pick(allIcons)),
        provideCharts(withDefaultRegisterables()),
    ],
};
