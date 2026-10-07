import { Injectable, inject } from '@angular/core';
import { BehaviorSubject, Observable, of, throwError } from 'rxjs';
import { User } from '../models/user';
import { HttpResponse } from '@angular/common/http';
import { LocalStorageService } from './storage.service';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private storageService = inject(LocalStorageService);
  private currentUserSubject: BehaviorSubject<User>;
  public currentUser: Observable<User>;

  private users = [
    {
      id: 1,
      username: 'admin@email.com',
      password: 'admin@123',
      firstName: 'Sarah',
      lastName: 'Smith',
      token: 'admin-token',
    },
  ];

  constructor() {
    this.currentUserSubject = new BehaviorSubject<User>(
      (this.storageService.get('currentUser') as User) || ({} as User)
    );
    this.currentUser = this.currentUserSubject.asObservable();
  }

  public get currentUserValue(): User {
    return this.currentUserSubject.value;
  }

  login(username: string, password: string) {

    const user = this.users.find((u) => u.username === username && u.password === password);

    if (!user) {
      return this.error('Username or password is incorrect');
    } else {
      this.storageService.set('currentUser', user);
      this.currentUserSubject.next(user);
      return this.ok({
        id: user.id,
        username: user.username,
        firstName: user.firstName,
        lastName: user.lastName,
        token: user.token,
      });
    }


  }
  ok(body?: {
    id: number;
    username: string;
    firstName: string;
    lastName: string;
    token: string;
  }) {
    return of(new HttpResponse({ status: 200, body }));
  }
  error(message: string) {
    return throwError(message);
  }

  logout() {
    // remove user from local storage to log user out
    this.storageService.remove('currentUser');
    this.currentUserSubject.next({} as User);
    return of({ success: false });
  }
}
