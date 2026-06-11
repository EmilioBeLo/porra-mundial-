export interface Match {
  id: number;
  equipo_local: string;
  equipo_visitante: string;
  fecha_hora: string;
  grupo_o_fase: string;
  goles_local_real: number | null;
  goles_visitante_real: number | null;
  es_partido_doble: boolean;
}
