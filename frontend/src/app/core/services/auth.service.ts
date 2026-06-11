import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';
import { User } from '../models/user.model';

interface AuthResponse {
  access_token: string;
  token_type: string;
}

interface TokenPayload {
  sub: string;
  is_admin: boolean;
  user_id: number;
  exp: number;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly baseUrl = environment.apiUrl;

  private readonly _currentUser = signal<User | null>(null);
  private readonly _isLoggedIn = signal<boolean>(false);
  private readonly _isAdmin = signal<boolean>(false);

  readonly currentUser = this._currentUser.asReadonly();
  readonly isLoggedIn = this._isLoggedIn.asReadonly();
  readonly isAdmin = this._isAdmin.asReadonly();

  readonly userName = computed(() => this._currentUser()?.nombre ?? '');

  constructor() {
    this.loadFromToken();
  }

  login(nombre: string, password: string): void {
    this.http
      .post<AuthResponse>(`${this.baseUrl}/auth/login`, { nombre, password })
      .subscribe({
        next: (res) => {
          localStorage.setItem('token', res.access_token);
          this.loadFromToken();
          this.router.navigate(['/']);
        },
        error: (err) => {
          console.error('Login failed', err);
          this._loginError.set(err.error?.detail ?? 'Error al iniciar sesión');
        },
      });
  }

  private readonly _loginError = signal<string | null>(null);
  readonly loginError = this._loginError.asReadonly();

  private readonly _registerError = signal<string | null>(null);
  readonly registerError = this._registerError.asReadonly();

  register(nombre: string, password: string): void {
    this.http
      .post<AuthResponse>(`${this.baseUrl}/auth/register`, {
        nombre,
        password,
      })
      .subscribe({
        next: (res) => {
          localStorage.setItem('token', res.access_token);
          this.loadFromToken();
          this.router.navigate(['/']);
        },
        error: (err) => {
          console.error('Register failed', err);
          this._registerError.set(err.error?.detail ?? 'Error al registrarse');
        },
      });
  }

  logout(): void {
    localStorage.removeItem('token');
    this._currentUser.set(null);
    this._isLoggedIn.set(false);
    this._isAdmin.set(false);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }

  clearLoginError(): void {
    this._loginError.set(null);
  }

  clearRegisterError(): void {
    this._registerError.set(null);
  }

  private loadFromToken(): void {
    const token = this.getToken();
    if (!token) {
      this._isLoggedIn.set(false);
      this._isAdmin.set(false);
      this._currentUser.set(null);
      return;
    }

    try {
      const payload = this.decodeToken(token);

      if (payload.exp * 1000 < Date.now()) {
        this.logout();
        return;
      }

      this._isLoggedIn.set(true);
      this._isAdmin.set(payload.is_admin ?? false);
      this._currentUser.set({
        id: payload.user_id,
        nombre: payload.sub,
        puntos_totales: 0,
        aciertos_perfectos: 0,
        is_admin: payload.is_admin ?? false,
      });
    } catch {
      this.logout();
    }
  }

  private decodeToken(token: string): TokenPayload {
    const parts = token.split('.');
    if (parts.length !== 3) throw new Error('Invalid token');
    const payload = parts[1];
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decoded);
  }
}
