import { Injectable } from '@angular/core';
import { MatSnackBar, MatSnackBarConfig, MatSnackBarRef } from '@angular/material/snack-bar';

/**
 * Generic snackbar service, based on Material Snackbar.
 *
 * Importing this service will give access to the snackbar component.
 */
@Injectable({ providedIn: 'root' })
export class SnackbarService {
  durationInSeconds = 5;

  constructor(private _snackBar: MatSnackBar) {}

  /**
   * Opens the snackbar component.
   * @param {string} message
   * @param {string} action
   * @param {"primary" | "accent" | "warn"} type
   * @param {number} duration (in seconds)
   */
  openSnackBar(message: string, action?: string, type?: 'primary' | 'accent' | 'warn', duration: number = this.durationInSeconds): MatSnackBarRef<any> {
    const config: MatSnackBarConfig = {
      duration: duration * 1000,
      panelClass: [
        'mat-toolbar',
        type ? `mat-${type}` : null
      ]
    }
    return this._snackBar.open(message, action, config);
  }

}
