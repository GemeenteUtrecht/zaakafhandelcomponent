import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { WorkstackSummary } from '@gu/models';
import { FeaturesWorkstackService } from './features-workstack.service';
import { SnackbarService } from '@gu/components';

/**
 * <gu-features-workstack></gu-features-workstack>
 *
 * Shows workstack for the user.
 */
@Component({
    selector: 'gu-features-workstack',
    templateUrl: './features-workstack.component.html',
    styleUrls: ['./features-workstack.component.scss'],
})
export class FeaturesWorkstackComponent implements OnInit {
    isLoading: boolean;
    summaryData: WorkstackSummary;

    readonly errorMessage = 'Er is een fout opgetreden bij het ophalen van de werkvoorraad';

    /**
     * Constructor method.
     * @param {FeaturesWorkstackService} workstackService
     * @param {SnackbarService} snackbarService
     */
    constructor(
      private workstackService: FeaturesWorkstackService,
      private snackbarService: SnackbarService,) {
    }


    //
    // Angular lifecycle.
    //

    /**
     * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
     * ngOnInit() method to handle any additional initialization tasks.
     */
    ngOnInit(): void {
        this.getContextData();
    }

    //
    // Context.
    //

    /**
     * Fetches the workstack data.
     */
    getContextData(): void {
        this.workstackService.getWorkstackSummary().subscribe(
            (res) => {
              this.summaryData = res;
            }, this.reportError.bind(this)
        );

    }


    //
    // Error handling.
    //

    /**
     * Error callback.
     * @param res
     */
    reportError(res) {
        const errorMessage = res.error?.detail
            ? res.error.detail
            : res.error?.nonFieldErrors
                ? res.error.nonFieldErrors[0]
                : this.errorMessage;

        this.isLoading = false;
        this.snackbarService.openSnackBar(errorMessage, 'Sluiten', 'warn');
        console.error(res);
    }
}
