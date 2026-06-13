import { Component, inject, OnInit, signal, computed, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ApiService } from '../../core/services/api.service';
import { Match } from '../../core/models/match.model';
import { Prediction, PredictionCreate } from '../../core/models/prediction.model';
import { CountdownPipe } from '../../shared/pipes/countdown.pipe';
import { LoadingSpinnerComponent } from '../../shared/components/loading-spinner/loading-spinner.component';

interface MatchWithPrediction {
  match: Match;
  prediction: Prediction | null;
  golesLocalPred: number | null;
  golesVisitantePred: number | null;
  isSaving: boolean;
  saveSuccess: boolean;
  saveError: string | null;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, CountdownPipe, LoadingSpinnerComponent],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
})
export class DashboardComponent implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);
  private readonly api = inject(ApiService);

  readonly loading = signal(true);
  readonly matchesWithPredictions = signal<MatchWithPrediction[]>([]);

  readonly showCommunityModal = signal(false);
  readonly selectedMatchForModal = signal<Match | null>(null);
  readonly communityPredictions = signal<any[]>([]);
  readonly loadingCommunity = signal(false);
  readonly communityError = signal<string | null>(null);

  readonly sortBy = signal<'date' | 'group'>('date');
  readonly selectedGroup = signal<string>('all');
  readonly teamQuery = signal<string>('');

  private countdownInterval: ReturnType<typeof setInterval> | null = null;
  readonly now = signal(Date.now());

  readonly nextMatch = computed(() => {
    const items = this.matchesWithPredictions();
    const upcoming = items
      .filter((m) => new Date(m.match.fecha_hora).getTime() > this.now())
      .sort((a, b) => new Date(a.match.fecha_hora).getTime() - new Date(b.match.fecha_hora).getTime());
    return upcoming.length > 0 ? upcoming[0].match : null;
  });

  readonly uniqueGroups = computed(() => {
    const phases = this.matchesWithPredictions().map(m => m.match.grupo_o_fase);
    return Array.from(new Set(phases)).sort();
  });

  readonly filteredMatches = computed(() => {
    let list = this.matchesWithPredictions();
    
    // Group filter
    const g = this.selectedGroup();
    if (g && g !== 'all') {
      list = list.filter(m => m.match.grupo_o_fase === g);
    }
    
    // Team query filter
    const query = this.teamQuery().toLowerCase().trim();
    if (query) {
      list = list.filter(m => 
        m.match.equipo_local.toLowerCase().includes(query) || 
        m.match.equipo_visitante.toLowerCase().includes(query)
      );
    }
    
    // Default sorting by date ascending
    return [...list].sort((a, b) => new Date(a.match.fecha_hora).getTime() - new Date(b.match.fecha_hora).getTime());
  });

  readonly groupedMatches = computed(() => {
    const list = this.filteredMatches();
    const groups: Record<string, MatchWithPrediction[]> = {};
    for (const item of list) {
      const phase = item.match.grupo_o_fase || 'Sin fase';
      if (!groups[phase]) {
        groups[phase] = [];
      }
      groups[phase].push(item);
    }
    return Object.keys(groups).map(key => ({
      groupName: key,
      matches: groups[key]
    }));
  });

  ngOnInit(): void {
    this.loadData();
    this.countdownInterval = setInterval(() => {
      this.now.set(Date.now());
    }, 30000);
  }

  ngOnDestroy(): void {
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
    }
  }

  private loadData(): void {
    this.loading.set(true);
    this.api.getMatches().subscribe({
      next: (matches) => {
        if (this.auth.isLoggedIn()) {
          this.api.getMyPredictions().subscribe({
            next: (predictions) => {
              this.buildMatchList(matches, predictions);
              this.loading.set(false);
            },
            error: () => {
              this.buildMatchList(matches, []);
              this.loading.set(false);
            },
          });
        } else {
          this.buildMatchList(matches, []);
          this.loading.set(false);
        }
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  private buildMatchList(matches: Match[], predictions: Prediction[]): void {
    const predMap = new Map<number, Prediction>();
    for (const p of predictions) {
      predMap.set(p.match_id, p);
    }

    const items: MatchWithPrediction[] = matches.map((m) => {
      const pred = predMap.get(m.id) ?? null;
      return {
        match: m,
        prediction: pred,
        golesLocalPred: pred?.goles_local_pred ?? null,
        golesVisitantePred: pred?.goles_visitante_pred ?? null,
        isSaving: false,
        saveSuccess: false,
        saveError: null,
      };
    });

    this.matchesWithPredictions.set(items);
  }

  isDeadlinePassed(match: Match): boolean {
    return new Date(match.fecha_hora).getTime() <= this.now();
  }

  hasResult(match: Match): boolean {
    return match.goles_local_real !== null && match.goles_visitante_real !== null;
  }

  getPointsBadgeClass(item: MatchWithPrediction): string {
    if (!item.prediction || !this.hasResult(item.match)) return 'badge-pending';
    const pts = item.prediction.puntos_obtenidos;
    if (pts >= (item.match.es_partido_doble ? 6 : 3)) return 'badge-perfect';
    if (pts > 0) return 'badge-tendency';
    return 'badge-miss';
  }

  getPointsLabel(item: MatchWithPrediction): string {
    if (!item.prediction) return 'Sin pronóstico';
    if (!this.hasResult(item.match)) return 'Pendiente';
    return `${item.prediction.puntos_obtenidos} pts`;
  }

  savePrediction(item: MatchWithPrediction): void {
    if (item.golesLocalPred === null || item.golesVisitantePred === null) return;
    if (item.golesLocalPred < 0 || item.golesVisitantePred < 0) return;

    item.isSaving = true;
    item.saveError = null;
    item.saveSuccess = false;

    const pred: PredictionCreate = {
      match_id: item.match.id,
      goles_local_pred: item.golesLocalPred,
      goles_visitante_pred: item.golesVisitantePred,
    };

    this.api.savePrediction(pred).subscribe({
      next: (saved) => {
        item.prediction = saved;
        item.isSaving = false;
        item.saveSuccess = true;
        setTimeout(() => (item.saveSuccess = false), 3000);
      },
      error: (err) => {
        item.isSaving = false;
        item.saveError = err.error?.detail ?? 'Error al guardar';
        setTimeout(() => (item.saveError = null), 5000);
      },
    });
  }

  openCommunityPredictions(match: Match): void {
    this.selectedMatchForModal.set(match);
    this.showCommunityModal.set(true);
    this.loadingCommunity.set(true);
    this.communityError.set(null);
    this.communityPredictions.set([]);

    this.api.getCommunityPredictions(match.id).subscribe({
      next: (preds) => {
        this.communityPredictions.set(preds);
        this.loadingCommunity.set(false);
      },
      error: (err) => {
        this.communityError.set(err.error?.detail ?? 'Error al cargar los pronósticos de la comunidad');
        this.loadingCommunity.set(false);
      },
    });
  }

  closeCommunityModal(): void {
    this.showCommunityModal.set(false);
    this.selectedMatchForModal.set(null);
    this.communityPredictions.set([]);
    this.communityError.set(null);
    this.loadingCommunity.set(false);
  }
}
