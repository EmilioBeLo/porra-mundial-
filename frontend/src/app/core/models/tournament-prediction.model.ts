export interface TournamentPrediction {
  id: number;
  user_id: number;
  campeon: string;
  subcampeon: string;
  maximo_goleador: string;
  maximo_asistente: string;
  created_at?: string;
}

export interface TournamentPredictionCreate {
  campeon: string;
  subcampeon: string;
  maximo_goleador: string;
  maximo_asistente: string;
}

export interface CommunityTournamentPrediction {
  username: string;
  campeon: string;
  subcampeon: string;
  maximo_goleador: string;
  maximo_asistente: string;
}

export interface TournamentResults {
  real_campeon: string;
  real_subcampeon: string;
  real_maximo_goleador: string;
  real_maximo_asistente: string;
}
