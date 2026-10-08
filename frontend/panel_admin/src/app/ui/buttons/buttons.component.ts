import { Component, OnInit, inject } from '@angular/core';
import { UntypedFormBuilder, UntypedFormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { JsonPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
@Component({
    selector: 'app-buttons',
    templateUrl: './buttons.component.html',
    styleUrls: ['./buttons.component.sass'],
    imports: [
        RouterLink,
        FormsModule,
        ReactiveFormsModule,
        JsonPipe,
    ]
})
export class ButtonsComponent implements OnInit {
  public checkboxGroupForm!: UntypedFormGroup;
  public radioGroupForm!: UntypedFormGroup;

  private formBuilder = inject(UntypedFormBuilder);
  model = {
    left: true,
    middle: false,
    right: false,
  };
  // Radio Buttons
  modelRadio = 1;
  ngOnInit() {
    this.checkboxGroupForm = this.formBuilder.group({
      left: true,
      middle: false,
      right: false,
    });
    this.radioGroupForm = this.formBuilder.group({
      modelRadioForm: 'Left',
    });
  }
}
