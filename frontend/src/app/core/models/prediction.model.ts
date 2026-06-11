export interface Prediction {
  id: number;
  user_id: number;
  match_id: number;
  goles_local_pred: number;
  goles_visitante_pred: number;
  puntos_obtenidos: number;
}

export interface PredictionCreate {
  match_id: number;
  goles_local_pred: number;
  goles_visitante_pred: number;
}
