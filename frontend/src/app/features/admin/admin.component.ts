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
  
  // Draw Teams States
  readonly drawingTeams = signal(false);
  readonly drawMsg = signal<string | null>(null);
  readonly drawMsgType = signal<'success' | 'error' | null>(null);
  readonly showConfirmDrawModal = signal(false);

  readonly filterFase = signal('');
  readonly showCreateForm = signal(false);

  // Competitions State
  readonly competitions = signal<{ league_id: number; name: string; season: number }[]>([]);
  readonly activeCompetition = signal<{ league_id: number; name: string; season: number } | null>(null);
  readonly changingCompetition = signal<boolean>(false);
  readonly competitionMsg = signal<string | null>(null);
  readonly competitionMsgType = signal<'success' | 'error' | null>(null);

  // Tournament Results States
  readonly realCampeon = signal('');
  readonly realSubcampeon = signal('');
  readonly realMaximoGoleador = signal('');
  readonly realMaximoAsistente = signal('');
  readonly savingTournamentResults = signal(false);
  readonly tournamentResultsMsg = signal<string | null>(null);
  readonly tournamentResultsMsgType = signal<'success' | 'error' | null>(null);
  readonly teams = signal<string[]>([]);

  // Tournament Lock States
  readonly isTournamentLocked = signal<boolean>(true);
  readonly togglingLock = signal<boolean>(false);
  readonly lockMsg = signal<string | null>(null);
  readonly lockMsgType = signal<'success' | 'error' | null>(null);

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
    this.loadTournamentResults();
    this.loadTournamentLock();
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

        const teamNames = new Set<string>();
        for (const m of matches) {
          if (m.equipo_local) teamNames.add(m.equipo_local);
          if (m.equipo_visitante) teamNames.add(m.equipo_visitante);
        }
        this.teams.set(Array.from(teamNames).sort());

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

  confirmDraw(): void {
    this.showConfirmDrawModal.set(true);
  }

  closeDrawModal(): void {
    this.showConfirmDrawModal.set(false);
  }

  executeDraw(): void {
    this.drawingTeams.set(true);
    this.drawMsg.set(null);
    this.showConfirmDrawModal.set(false);

    this.api.drawTeams().subscribe({
      next: () => {
        this.drawingTeams.set(false);
        this.drawMsg.set('Sorteo completado con éxito. ¡Se asignaron las selecciones!');
        this.drawMsgType.set('success');
        setTimeout(() => {
          this.drawMsg.set(null);
          this.drawMsgType.set(null);
        }, 5000);
      },
      error: (err) => {
        this.drawingTeams.set(false);
        this.drawMsg.set(err.error?.detail ?? 'Error al realizar el sorteo');
        this.drawMsgType.set('error');
        setTimeout(() => {
          this.drawMsg.set(null);
          this.drawMsgType.set(null);
        }, 5000);
      }
    });
  }

  submitTournamentResults(): void {
    this.savingTournamentResults.set(true);
    this.tournamentResultsMsg.set(null);

    const payload = {
      real_campeon: this.realCampeon().trim(),
      real_subcampeon: this.realSubcampeon().trim(),
      real_maximo_goleador: this.realMaximoGoleador().trim(),
      real_maximo_asistente: this.realMaximoAsistente().trim(),
    };

    this.api.saveTournamentResults(payload).subscribe({
      next: (res) => {
        this.savingTournamentResults.set(false);
        this.tournamentResultsMsg.set('Resultados del torneo guardados y puntos recalculados exitosamente.');
        this.tournamentResultsMsgType.set('success');
        setTimeout(() => {
          this.tournamentResultsMsg.set(null);
          this.tournamentResultsMsgType.set(null);
        }, 5000);
      },
      error: (err) => {
        this.savingTournamentResults.set(false);
        this.tournamentResultsMsg.set(err.error?.detail ?? 'Error al guardar los resultados del torneo');
        this.tournamentResultsMsgType.set('error');
        setTimeout(() => {
          this.tournamentResultsMsg.set(null);
          this.tournamentResultsMsgType.set(null);
        }, 5000);
      }
    });
  }

  private loadTournamentResults(): void {
    this.api.getTournamentResults().subscribe({
      next: (res) => {
        if (res) {
          this.realCampeon.set(res.real_campeon || '');
          this.realSubcampeon.set(res.real_subcampeon || '');
          this.realMaximoGoleador.set(res.real_maximo_goleador || '');
          this.realMaximoAsistente.set(res.real_maximo_asistente || '');
        }
      },
      error: (err) => console.error('Error loading tournament results in admin component', err)
    });
  }

  private loadTournamentLock(): void {
    this.api.getTournamentLock().subscribe({
      next: (res) => this.isTournamentLocked.set(res.locked),
      error: (err) => console.error('Error loading tournament lock status', err)
    });
  }

  toggleLock(): void {
    this.togglingLock.set(true);
    this.lockMsg.set(null);

    this.api.toggleTournamentLock().subscribe({
      next: (res) => {
        this.isTournamentLocked.set(res.locked);
        this.togglingLock.set(false);
        this.lockMsg.set(res.locked ? "Predicciones del torneo bloqueadas" : "Predicciones del torneo desbloqueadas");
        this.lockMsgType.set('success');
        setTimeout(() => {
          this.lockMsg.set(null);
          this.lockMsgType.set(null);
        }, 4000);
      },
      error: (err) => {
        this.togglingLock.set(false);
        this.lockMsg.set(err.error?.detail ?? 'Error al cambiar el bloqueo del torneo');
        this.lockMsgType.set('error');
        setTimeout(() => {
          this.lockMsg.set(null);
          this.lockMsgType.set(null);
        }, 5000);
      }
    });
  }
}
