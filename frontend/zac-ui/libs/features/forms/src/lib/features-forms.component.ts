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
  /** @type {Form[]} The forms. */
  forms: Form[] = [];

  /** @type {Table} The table data. */
  tableData: Table = null;

  /**
   * Constructor method.
   * @param featuresFormsService
   */
  constructor(
    private featuresFormsService: FeaturesFormsService,
  ) { }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive.
   * Define an `ngOnInit()` method to handle any additional initialization tasks.
   */
  ngOnInit() {
    this.getContextData();
  }

  //
  // Context.
  //

  /**
   * Fetches the forms and gets the table data.
   */
  getContextData() {
    this.featuresFormsService.getForms().subscribe(
      (data) => {
        this.forms = data;
        this.tableData = this.getTableData();
      },
      (error) => console.error(error),
    );
  }

  /**
   * Return the table data for the forms table.
   * @return {Table}
   */
  getTableData(): Table {
    return {
      headData: ['Naam', 'URL'],
      bodyData: this.getBodyData(),
    }
  }

  /**
   * Returns the RowData[] for use in the table's bodyData.
   * @return RowData[]
   */
  getBodyData(): RowData[] {
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

  //
  // Events.
  //

  onSort(sortData) {
    const key = (sortData.value.toUpperCase() === 'URL') ? 'slug' : sortData.value;
    const order = sortData.order.toUpperCase();

    this.forms = this.forms.sort((a, b) => {
      const valueA = String(a[key]).toUpperCase();
      const valueB = String(b[key]).toUpperCase();

      if (valueA < valueB) {
        return (order === 'ASC') ? -1 : 1;
      }
      if (valueA > valueB) {
        return (order === 'ASC') ? 1 : -1;
      }
      return 0;
    })

    this.tableData = this.getTableData();
  }
}
