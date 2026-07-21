export interface User {
  id: number;
  nombre: string;
  puntos_totales: number;
  aciertos_perfectos: number;
  is_admin: boolean;
  posicion?: number;
  assigned_team?: string | null;
  puntos_underdog?: number;
  puntos_predicciones?: number;
  puntos_torneo?: number;
  puntos_campeon?: number;
  puntos_subcampeon?: number;
  puntos_goleador?: number;
  puntos_asistente?: number;
}
