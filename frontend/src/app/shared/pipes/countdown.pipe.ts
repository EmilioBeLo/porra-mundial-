import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'countdown',
  standalone: true,
  pure: false,
})
export class CountdownPipe implements PipeTransform {
  transform(targetDate: string | null | undefined): string {
    if (!targetDate) return '';

    const target = new Date(targetDate).getTime();
    const now = Date.now();
    const diff = target - now;

    if (diff <= 0) return 'Cerrado';

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    }
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  }
}
