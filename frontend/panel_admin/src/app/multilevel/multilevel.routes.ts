import { First3Component } from './first3/first3.component';
import { First2Component } from './first2/first2.component';
import { First1Component } from './first1/first1.component';
import { Second2Component } from './secondlevel/second2/second2.component';
import { Second1Component } from './secondlevel/second1/second1.component';
import { Third1Component } from './thirdlevel/third1/third1.component';
import { Route } from '@angular/router';

export const MULTILEVEL_ROUTE: Route[] = [
  {
    path: 'first1',
    component: First1Component,
  },
  {
    path: 'first2',
    component: First2Component,
  },
  {
    path: 'first3',
    component: First3Component,
  },
  {
    path: 'secondlevel/second1',
    component: Second1Component,
  },
  {
    path: 'secondlevel/second2',
    component: Second2Component,
  },
  {
    path: 'thirdlevel/third1',
    component: Third1Component,
  },
];

