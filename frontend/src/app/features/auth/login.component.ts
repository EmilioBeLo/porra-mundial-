import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent {
  readonly auth = inject(AuthService);

  nombre = '';
  password = '';

  onSubmit(): void {
    if (!this.nombre.trim() || !this.password.trim()) return;
    this.auth.clearLoginError();
    this.auth.login(this.nombre.trim(), this.password);
  }
}
