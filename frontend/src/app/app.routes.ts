import { Routes } from '@angular/router';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { LeaderboardComponent } from './features/leaderboard/leaderboard.component';
import { AdminComponent } from './features/admin/admin.component';
import { LoginComponent } from './features/auth/login.component';
import { RulesComponent } from './features/rules/rules.component';
import { adminGuard } from './core/guards/admin.guard';

export const routes: Routes = [
  { path: '', component: DashboardComponent },
  { path: 'leaderboard', component: LeaderboardComponent },
  { path: 'rules', component: RulesComponent },
  { path: 'admin', component: AdminComponent, canActivate: [adminGuard] },
  { path: 'login', component: LoginComponent },
  { path: 'register', redirectTo: 'login' },
  { path: '**', redirectTo: '' },
];

