import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.css',
})
export class NavbarComponent {
  readonly auth = inject(AuthService);
  readonly mobileMenuOpen = signal(false);

  toggleMenu(): void {
    this.mobileMenuOpen.update((v) => !v);
  }

  closeMenu(): void {
    this.mobileMenuOpen.set(false);
  }

  logout(): void {
    this.closeMenu();
    this.auth.logout();
  }
}
