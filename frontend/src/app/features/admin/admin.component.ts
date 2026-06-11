import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { Match } from '../../core/models/match.model';
import { LoadingSpinnerComponent } from '../../shared/components/loading-spinner/loading-spinner.component';

interface MatchAdmin extends Match {
  editGolesLocal: number | null;
  editGolesVisitante: number | null;
  isSaving: boolean;
  saveMsg: string | null;
  saveMsgType: 'success' | 'error' | null;
}

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, LoadingSpinnerComponent],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css',
})
export class AdminComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly loading = signal(true);
  readonly matches = signal<MatchAdmin[]>([]);

  // API-Football Integration States
  readonly syncingMatches = signal(false);
  readonly syncMatchesMsg = signal<string | null>(null);
  readonly syncMatchesMsgType = signal<'success' | 'error' | null>(null);

  readonly syncingResults = signal(false);
  readonly syncResultsMsg = signal<string | null>(null);
  readonly syncResultsMsgType = signal<'success' | 'error' | null>(null);
  readonly filterFase = signal('');
  readonly showCreateForm = signal(false);

  // Competitions State
  readonly competitions = signal<{ league_id: number; name: string; season: number }[]>([]);
  readonly activeCompetition = signal<{ league_id: number; name: string; season: number } | null>(null);
  readonly changingCompetition = signal<boolean>(false);
  readonly competitionMsg = signal<string | null>(null);
  readonly competitionMsgType = signal<'success' | 'error' | null>(null);

  // Create match form
  newMatch = {
    equipo_local: '',
    equipo_visitante: '',
    fecha_hora: '',
    grupo_o_fase: '',
    es_partido_doble: false,
  };
  readonly creating = signal(false);
  readonly createMsg = signal<string | null>(null);
  readonly createMsgType = signal<'success' | 'error' | null>(null);

  readonly fases = signal<string[]>([]);

  ngOnInit(): void {
    this.loadMatches();
    this.loadCompetitions();
  }

  private loadCompetitions(): void {
    this.api.getCompetitions().subscribe({
      next: (res) => this.competitions.set(res),
      error: (err) => console.error('Error loading competitions', err)
    });
    this.api.getActiveCompetition().subscribe({
      next: (res) => this.activeCompetition.set(res),
      error: (err) => console.error('Error loading active competition', err)
    });
  }

  changeCompetition(leagueId: number): void {
    this.changingCompetition.set(true);
    this.competitionMsg.set(null);

    this.api.setActiveCompetition(leagueId).subscribe({
      next: (res) => {
        this.activeCompetition.set(res);
        this.competitionMsg.set("Competición cambiada exitosamente. ¡Puntos recalculados!");
        this.competitionMsgType.set('success');
        this.loadMatches();
        this.changingCompetition.set(false);

        setTimeout(() => {
          this.competitionMsg.set(null);
          this.competitionMsgType.set(null);
        }, 5000);
      },
      error: (err) => {
        this.changingCompetition.set(false);
        this.competitionMsg.set(err.error?.detail ?? 'Error al cambiar la competición');
        this.competitionMsgType.set('error');

        setTimeout(() => {
          this.competitionMsg.set(null);
          this.competitionMsgType.set(null);
        }, 5000);
      }
    });
  }

  private loadMatches(): void {
    this.loading.set(true);
    this.api.getMatches().subscribe({
      next: (matches) => {
        const adminMatches: MatchAdmin[] = matches.map((m) => ({
          ...m,
          editGolesLocal: m.goles_local_real,
          editGolesVisitante: m.goles_visitante_real,
          isSaving: false,
          saveMsg: null,
          saveMsgType: null,
        }));
        this.matches.set(adminMatches);

        const fasesSet = new Set(matches.map((m) => m.grupo_o_fase).filter(Boolean));
        this.fases.set(Array.from(fasesSet).sort());

        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  get filteredMatches(): MatchAdmin[] {
    const fase = this.filterFase();
    if (!fase) return this.matches();
    return this.matches().filter((m) => m.grupo_o_fase === fase);
  }

  submitResult(match: MatchAdmin): void {
    if (match.editGolesLocal === null || match.editGolesVisitante === null) return;
    if (match.editGolesLocal < 0 || match.editGolesVisitante < 0) return;

    match.isSaving = true;
    match.saveMsg = null;

    this.api.submitResult(match.id, match.editGolesLocal, match.editGolesVisitante).subscribe({
      next: () => {
        match.goles_local_real = match.editGolesLocal;
        match.goles_visitante_real = match.editGolesVisitante;
        match.isSaving = false;
        match.saveMsg = 'Resultado guardado correctamente';
        match.saveMsgType = 'success';
        setTimeout(() => {
          match.saveMsg = null;
          match.saveMsgType = null;
        }, 4000);
      },
      error: (err) => {
        match.isSaving = false;
        match.saveMsg = err.error?.detail ?? 'Error al guardar resultado';
        match.saveMsgType = 'error';
        setTimeout(() => {
          match.saveMsg = null;
          match.saveMsgType = null;
        }, 5000);
      },
    });
  }

  toggleCreateForm(): void {
    this.showCreateForm.update((v) => !v);
  }

  createMatch(): void {
    if (
      !this.newMatch.equipo_local.trim() ||
      !this.newMatch.equipo_visitante.trim() ||
      !this.newMatch.fecha_hora
    ) {
      return;
    }

    this.creating.set(true);
    this.createMsg.set(null);

    this.api.createMatch({
      equipo_local: this.newMatch.equipo_local.trim(),
      equipo_visitante: this.newMatch.equipo_visitante.trim(),
      fecha_hora: this.newMatch.fecha_hora,
      grupo_o_fase: this.newMatch.grupo_o_fase.trim(),
      es_partido_doble: this.newMatch.es_partido_doble,
    }).subscribe({
      next: () => {
        this.creating.set(false);
        this.createMsg.set('Partido creado exitosamente');
        this.createMsgType.set('success');
        this.newMatch = {
          equipo_local: '',
          equipo_visitante: '',
          fecha_hora: '',
          grupo_o_fase: '',
          es_partido_doble: false,
        };
        this.loadMatches();
        setTimeout(() => {
          this.createMsg.set(null);
          this.createMsgType.set(null);
        }, 4000);
      },
      error: (err) => {
        this.creating.set(false);
        this.createMsg.set(err.error?.detail ?? 'Error al crear partido');
        this.createMsgType.set('error');
        setTimeout(() => {
          this.createMsg.set(null);
          this.createMsgType.set(null);
        }, 5000);
      },
    });
  }

  syncMatches(): void {
    this.syncingMatches.set(true);
    this.syncMatchesMsg.set(null);
    this.api.syncMatches().subscribe({
      next: (res) => {
        this.syncingMatches.set(false);
        this.syncMatchesMsg.set(`Sincronizados ${res.synchronized} partidos del Mundial 2026`);
        this.syncMatchesMsgType.set('success');
        this.loadMatches();
        setTimeout(() => {
          this.syncMatchesMsg.set(null);
          this.syncMatchesMsgType.set(null);
        }, 5000);
      },
      error: (err) => {
        this.syncingMatches.set(false);
        this.syncMatchesMsg.set(err.error?.detail ?? 'Error al sincronizar partidos');
        this.syncMatchesMsgType.set('error');
        setTimeout(() => {
          this.syncMatchesMsg.set(null);
          this.syncMatchesMsgType.set(null);
        }, 5000);
      },
    });
  }

  syncResults(): void {
    this.syncingResults.set(true);
    this.syncResultsMsg.set(null);
    this.api.syncResults().subscribe({
      next: (res) => {
        this.syncingResults.set(false);
        this.syncResultsMsg.set(`Sincronizados resultados de ${res.updated_matches_count} partidos. ¡Pronósticos y clasificación recalculados!`);
        this.syncResultsMsgType.set('success');
        this.loadMatches();
        setTimeout(() => {
          this.syncResultsMsg.set(null);
          this.syncResultsMsgType.set(null);
        }, 5000);
      },
      error: (err) => {
        this.syncingResults.set(false);
        this.syncResultsMsg.set(err.error?.detail ?? 'Error al actualizar resultados');
        this.syncResultsMsgType.set('error');
        setTimeout(() => {
          this.syncResultsMsg.set(null);
          this.syncResultsMsgType.set(null);
        }, 5000);
      },
    });
  }
}
