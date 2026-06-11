import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { User } from '../../core/models/user.model';
import { LoadingSpinnerComponent } from '../../shared/components/loading-spinner/loading-spinner.component';

@Component({
  selector: 'app-leaderboard',
  standalone: true,
  imports: [CommonModule, LoadingSpinnerComponent],
  templateUrl: './leaderboard.component.html',
  styleUrl: './leaderboard.component.css',
})
export class LeaderboardComponent implements OnInit {
  private readonly api = inject(ApiService);
  readonly auth = inject(AuthService);

  readonly loading = signal(true);
  readonly users = signal<User[]>([]);

  readonly sortedUsers = computed(() => {
    return [...this.users()]
      .sort((a, b) => {
        if (b.puntos_totales !== a.puntos_totales) return b.puntos_totales - a.puntos_totales;
        return b.aciertos_perfectos - a.aciertos_perfectos;
      })
      .map((u, i) => ({ ...u, posicion: i + 1 }));
  });

  readonly podium = computed(() => this.sortedUsers().slice(0, 3));
  readonly rest = computed(() => this.sortedUsers().slice(3));

  readonly currentUserId = computed(() => this.auth.currentUser()?.id ?? -1);

  ngOnInit(): void {
    this.api.getUsers().subscribe({
      next: (users) => {
        this.users.set(users);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  getMedalEmoji(pos: number): string {
    switch (pos) {
      case 1: return '🥇';
      case 2: return '🥈';
      case 3: return '🥉';
      default: return '';
    }
  }

  getMedalGradient(pos: number): string {
    switch (pos) {
      case 1: return 'from-amber-400 to-yellow-600';
      case 2: return 'from-slate-300 to-slate-500';
      case 3: return 'from-amber-600 to-amber-800';
      default: return 'from-slate-600 to-slate-700';
    }
  }

  getPodiumHeight(pos: number): string {
    switch (pos) {
      case 1: return 'h-28';
      case 2: return 'h-20';
      case 3: return 'h-16';
      default: return 'h-12';
    }
  }
}
