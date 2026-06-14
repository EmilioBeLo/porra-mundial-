import { Component } from '@angular/core';

@Component({
  selector: 'app-loading-spinner',
  standalone: true,
  template: `
    <div class="flex items-center justify-center py-12" id="loading-spinner">
      <div class="relative w-28 h-28 flex items-center justify-center">
        <!-- Image spinner -->
        <img 
          src="amigo.png" 
          class="w-28 h-28 rounded-full object-cover animate-spin shadow-lg border-2 border-amber-500/20" 
          alt="Cargando..."
          #friendImg
          (error)="friendImg.style.display='none'; fallbackSpinner.style.display='block'"
        >
        <!-- Fallback CSS double spinner, hidden by default unless image errors out -->
        <div #fallbackSpinner class="relative hidden">
          <div class="w-12 h-12 rounded-full border-2 border-white/10 border-t-accent-500 animate-spin"></div>
          <div class="absolute inset-0 w-12 h-12 rounded-full border-2 border-transparent border-b-accent-300 animate-spin" style="animation-duration: 1.5s; animation-direction: reverse;"></div>
        </div>
      </div>
    </div>
  `,
})
export class LoadingSpinnerComponent {}
