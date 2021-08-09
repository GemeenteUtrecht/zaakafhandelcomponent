import { Injectable } from '@angular/core';
import { MatSnackBar, MatSnackBarConfig } from '@angular/material/snack-bar';

@Injectable({ providedIn: 'root' })
export class SnackbarService {
  durationInSeconds = 5;

  constructor(private _snackBar: MatSnackBar) {}

  openSnackBar(message: string, action?: string, type?: 'primary' | 'accent' | 'warn', duration: number = this.durationInSeconds) {
    const config: MatSnackBarConfig = {
      duration: duration * 1000,
      panelClass: [
        'mat-toolbar',
        type ? `mat-${type}` : null
      ]
    }
    this._snackBar.open(message, action, config);
  }

}
