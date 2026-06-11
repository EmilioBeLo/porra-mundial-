import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrl: './register.component.css',
})
export class RegisterComponent {
  readonly auth = inject(AuthService);

  nombre = '';
  password = '';
  confirmPassword = '';

  get passwordMismatch(): boolean {
    return this.confirmPassword.length > 0 && this.password !== this.confirmPassword;
  }

  get canSubmit(): boolean {
    return (
      this.nombre.trim().length > 0 &&
      this.password.length >= 4 &&
      this.password === this.confirmPassword
    );
  }

  onSubmit(): void {
    if (!this.canSubmit) return;
    this.auth.clearRegisterError();
    this.auth.register(this.nombre.trim(), this.password);
  }
}
