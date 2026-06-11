import { Component, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Match } from '../../core/models/match.model';
import { Prediction } from '../../core/models/prediction.model';
import { CountdownPipe } from '../../shared/pipes/countdown.pipe';

@Component({
  selector: 'app-prediction-card',
  standalone: true,
  imports: [FormsModule, CountdownPipe],
  templateUrl: './prediction-card.component.html',
  styleUrl: './prediction-card.component.css',
})
export class PredictionCardComponent {
  readonly match = input.required<Match>();
  readonly prediction = input<Prediction | null>(null);
  readonly isLoggedIn = input(false);
  readonly isEditable = input(false);

  readonly save = output<{ matchId: number; golesLocal: number; golesVisitante: number }>();

  golesLocal: number | null = null;
  golesVisitante: number | null = null;

  ngOnInit(): void {
    const pred = this.prediction();
    if (pred) {
      this.golesLocal = pred.goles_local_pred;
      this.golesVisitante = pred.goles_visitante_pred;
    }
  }

  onSave(): void {
    if (this.golesLocal === null || this.golesVisitante === null) return;
    this.save.emit({
      matchId: this.match().id,
      golesLocal: this.golesLocal,
      golesVisitante: this.golesVisitante,
    });
  }

  hasResult(): boolean {
    const m = this.match();
    return m.goles_local_real !== null && m.goles_visitante_real !== null;
  }
}
