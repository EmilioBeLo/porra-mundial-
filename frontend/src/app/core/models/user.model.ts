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
}
