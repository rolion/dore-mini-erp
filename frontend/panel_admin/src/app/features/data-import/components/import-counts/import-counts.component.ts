import { Component, input } from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';
import { ImportCounts } from '../../models/sales-import';

/** Contadores del resultado de una importación: cargadas, ya importadas, sin asiento y con error. */
@Component({
  selector: 'app-import-counts',
  imports: [TranslatePipe],
  template: `
    <dl class="row mb-3" data-testid="import-counts">
      <dt class="col-8 col-sm-4 col-lg-3">{{ 'DATA_IMPORT.COUNT_CREATED' | translate }}</dt>
      <dd class="col-4 col-sm-2 col-lg-3" data-testid="count-created">{{ counts().created }}</dd>
      <dt class="col-8 col-sm-4 col-lg-3">{{ 'DATA_IMPORT.COUNT_SKIPPED' | translate }}</dt>
      <dd class="col-4 col-sm-2 col-lg-3" data-testid="count-skipped">{{ counts().skipped }}</dd>
      <dt class="col-8 col-sm-4 col-lg-3">{{ 'DATA_IMPORT.COUNT_WITHOUT_POSTING' | translate }}</dt>
      <dd class="col-4 col-sm-2 col-lg-3" data-testid="count-without-posting">{{ counts().withoutPosting }}</dd>
      <dt class="col-8 col-sm-4 col-lg-3">{{ 'DATA_IMPORT.COUNT_FAILED' | translate }}</dt>
      <dd class="col-4 col-sm-2 col-lg-3" data-testid="count-failed">{{ counts().failed }}</dd>
    </dl>
  `,
})
export class ImportCountsComponent {
  readonly counts = input.required<ImportCounts>();
}
