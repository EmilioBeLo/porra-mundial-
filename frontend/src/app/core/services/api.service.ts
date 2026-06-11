import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { User } from '../models/user.model';
import { Match } from '../models/match.model';
import { Prediction, PredictionCreate } from '../models/prediction.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  // --- Users ---
  getUsers(): Observable<User[]> {
    return this.http.get<User[]>(`${this.baseUrl}/users`);
  }

  // --- Matches ---
  getMatches(fase?: string): Observable<Match[]> {
    let params = new HttpParams();
    if (fase) {
      params = params.set('fase', fase);
    }
    return this.http.get<Match[]>(`${this.baseUrl}/matches`, { params });
  }

  getMatch(id: number): Observable<Match> {
    return this.http.get<Match>(`${this.baseUrl}/matches/${id}`);
  }

  // --- Predictions ---
  savePrediction(pred: PredictionCreate): Observable<Prediction> {
    return this.http.post<Prediction>(`${this.baseUrl}/predictions`, pred);
  }

  getMyPredictions(): Observable<Prediction[]> {
    return this.http.get<Prediction[]>(`${this.baseUrl}/predictions/me`);
  }

  getUserPredictions(userId: number): Observable<Prediction[]> {
    return this.http.get<Prediction[]>(`${this.baseUrl}/predictions/user/${userId}`);
  }

  // --- Admin ---
  submitResult(matchId: number, goles_local: number, goles_visitante: number): Observable<{ match_id: number; predictions_updated: number; users_updated: number }> {
    return this.http.put<{ match_id: number; predictions_updated: number; users_updated: number }>(`${this.baseUrl}/admin/matches/${matchId}/result`, {
      goles_local_real: goles_local,
      goles_visitante_real: goles_visitante,
    });
  }

  createMatch(match: Partial<Match>): Observable<Match> {
    return this.http.post<Match>(`${this.baseUrl}/admin/matches`, match);
  }

  syncMatches(): Observable<{ status: string; synchronized: number }> {
    return this.http.post<{ status: string; synchronized: number }>(`${this.baseUrl}/admin/sync/matches`, {});
  }

  syncResults(): Observable<{ status: string; updated_matches_count: number }> {
    return this.http.post<{ status: string; updated_matches_count: number }>(`${this.baseUrl}/admin/sync/results`, {});
  }

  // --- Settings / Competitions ---
  getCompetitions(): Observable<{ league_id: number; name: string; season: number }[]> {
    return this.http.get<{ league_id: number; name: string; season: number }[]>(`${this.baseUrl}/settings/competitions`);
  }

  getActiveCompetition(): Observable<{ league_id: number; name: string; season: number }> {
    return this.http.get<{ league_id: number; name: string; season: number }>(`${this.baseUrl}/settings/active`);
  }

  setActiveCompetition(leagueId: number): Observable<{ league_id: number; name: string; season: number }> {
    return this.http.put<{ league_id: number; name: string; season: number }>(`${this.baseUrl}/settings/active`, { league_id: leagueId });
  }
}
