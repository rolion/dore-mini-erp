import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { EMPTY, catchError, finalize, switchMap } from 'rxjs';
import { confirmProfileState } from '../services/profile-confirmation';
import { Profile, ProfileKind } from '../models/profile';
import { PersonnelApiService, profileError } from '../services/personnel-api.service';

@Component({
  selector: 'app-personnel-detail', templateUrl: './profile-detail.component.html', imports: [RouterLink, DatePipe],
})
export class ProfileDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private api = inject(PersonnelApiService);
  private destroyRef = inject(DestroyRef);
  readonly kind = this.route.snapshot.data['kind'] as ProfileKind;
  readonly base = `/pocketbiz/personnel/${this.kind}`;
  profile: Profile | null = null;
  loading = false;
  saving = false;
  error = '';
  message = '';
  userName = '';

  ngOnInit(): void {
    this.message = typeof history.state?.message === 'string' ? history.state.message : '';
    this.route.paramMap.pipe(switchMap(params => {
      this.profile = null;
      this.loading = true;
      this.error = '';
      return this.api.get(this.kind, params.get('id') || '').pipe(
        catchError(error => { this.error = profileError(error); return EMPTY; }), finalize(() => this.loading = false),
      );
    }), takeUntilDestroyed(this.destroyRef)).subscribe(item => {
      this.profile = item;
      this.userName = '';
      if (item.user_id) this.api.users('', item.user_id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: users => this.userName = users[0]?.name || `Usuario #${item.user_id}`,
        error: () => this.userName = `Usuario #${item.user_id}`,
      });
    });
  }
  async toggle(): Promise<void> {
    if (!this.profile || this.saving) return;
    this.saving = true;
    const item = this.profile;
    if (!await confirmProfileState(item)) { this.saving = false; return; }
    this.error = '';
    this.api.setActive(this.kind, item).pipe(finalize(() => this.saving = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: updated => { this.profile = updated; this.message = updated.active ? 'Registro activado.' : 'Registro desactivado.'; },
      error: error => this.error = profileError(error),
    });
  }
}
