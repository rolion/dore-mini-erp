import { Route } from '@angular/router';
import { FormValidationComponent } from './form-validation/form-validation.component';
import { BasicFormComponent } from './basic-form/basic-form.component';
import { InputMaskComponent } from './input-mask/input-mask.component';
import { SelectItemComponent } from './select-item/select-item.component';
import { AdvanceControlComponent } from './advance-control/advance-control.component';
import { FormExampleComponent } from './form-example/form-example.component';
import { EditorsComponent } from './editors/editors.component';

export const FORMS_ROUTE: Route[] = [
  {
    path: 'basic',
    component: BasicFormComponent,
  },
  {
    path: 'advance-control',
    component: AdvanceControlComponent,
  },
  {
    path: 'form-example',
    component: FormExampleComponent,
  },
  {
    path: 'form-validation',
    component: FormValidationComponent,
  },
  {
    path: 'input-mask',
    component: InputMaskComponent,
  },
  {
    path: 'select-item',
    component: SelectItemComponent,
  },
  {
    path: 'editors',
    component: EditorsComponent,
  },
];
