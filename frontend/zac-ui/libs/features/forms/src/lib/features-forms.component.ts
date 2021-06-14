import {Component, OnInit} from '@angular/core';
import {RowData, Table} from '@gu/models';
import {FeaturesFormsService} from "./features-forms.service";
import {Form} from "./features-forms.model";

@Component({
  providers: [FeaturesFormsService],
  selector: 'gu-features-forms',
  templateUrl: './features-forms.component.html',
  styleUrls: ['./features-forms.component.scss'],
})
export class FeaturesFormsComponent implements OnInit {
  forms: Form[] = [];

  constructor(private featuresFormsService: FeaturesFormsService) {
  }

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive.
   * Define an `ngOnInit()` method to handle any additional initialization tasks.
   */
  ngOnInit() {
    this.featuresFormsService.getForms().subscribe(
      (data) => this.forms = data,
      (error) => console.error(error),
    );
  }

  /**
   * Return the table data for the forms table.
   * @return {Table}
   */
  get tableData(): Table {
    return {
      headData: ['Naam', 'URL'],
      bodyData: this.bodyData,
    }
  }

  /**
   * Returns the RowData[] for use in the table's bodyData.
   * @return RowData[]
   */
  get bodyData(): RowData[] {
    return this.forms.map(form => ({
        cellData: {
          'Naam': form.name,
          'URL': {
            type: "link",
            label: this.featuresFormsService.getAbsoluteFormURL(form),
            url: this.featuresFormsService.getAbsoluteFormURL(form),
            target: '_blank',
          },
        }
      }
    ));
  }
}
