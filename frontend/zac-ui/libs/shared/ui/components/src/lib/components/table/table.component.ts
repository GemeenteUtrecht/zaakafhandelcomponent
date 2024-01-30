import {animate, state, style, transition, trigger} from '@angular/animations';
import {AfterViewInit, Component, EventEmitter, Input, OnChanges, OnInit, Output, ViewChild} from '@angular/core';
import {MatSort} from '@angular/material/sort';
import {MatTableDataSource} from '@angular/material/table';
import { Column, ExtensiveCell, Table, TableSort, UserSearchResult } from '@gu/models';
import {TableService} from './table.service';
import {TableButtonClickEvent, TableSortEvent} from './table';
import {Choice} from '@gu/components';
import { SelectionModel } from '@angular/cdk/collections';
import { MatCheckboxChange } from '@angular/material/checkbox';


/**
 * <gu-table [table]="tableData"></gu-table>
 *
 * Generic table component, based on mat-table.
 *
 * Requires table: Table input for main tabular data.
 * Takes expandable: boolean as toggle to allow expanding rows (if available).
 * Takes sortable: boolean as toggle to allow sorting.
 * Takes wrap: boolean as toggle to allow wrapping.
 *
 * Emits buttonOutput: TableButtonClickEvent output when a button is clicked.
 * Emits sortOutput: SortEvent output when the table gets sorted.
 * Emits tableOutput: any output when a row is clicked.
 */
@Component({
    animations: [
        trigger('detailExpand', [
            state('collapsed', style({height: '0px', minHeight: '0'})),
            state('expanded', style({height: '*'})),
            transition('expanded <=> collapsed', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
        ]),
    ],
    providers: [TableService],
    selector: 'gu-table',
    styleUrls: ['./table.component.scss'],
    templateUrl: './table.component.html',
})
export class TableComponent implements OnInit, AfterViewInit, OnChanges {
    @Input() expandable = false;
    @Input() sortable = false;
    @Input() table: Table;
    @Input() wrap = false;
    @Input() preselectedValues = [];

    @Output() tableOutput = new EventEmitter<any>();
    @Output() buttonOutput = new EventEmitter<any>();
    @Output() sortOutput = new EventEmitter<any>();
    @Output() selectionOutput = new EventEmitter<any>();

    @ViewChild(MatSort) sort: MatSort;


    /** @type {Column[]} Columns to render, part of the data to show. */
    columns: Column[];

    /** @type {Column[]} Columns to render, part of the ui generated by this component. */
    uiColumns: { name: string, label: string }[];

    /** @type {string[]} The names of all columns in both this.columns as this.uicolumns. */
    displayedColumns: string[];

    /** @type {MatTableDataSource} The datasource for the mat-table. */
    dataSource: MatTableDataSource<any>;

    /** @type {number|null} The index of the row to expand. */
    expandedIndex: number | null;

    selectedValues: any[] = [];

    /**
     * Constructor method.
     * @param {TableService} tableService
     */
    constructor(private tableService: TableService) {
        this.table = this.table || {headData: [], bodyData: []};
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
        this.selectedValues = this.preselectedValues
    }

    /**
     * A lifecycle hook that is called after Angular has fully initialized a component's view. Define an ngAfterViewInit()
     * method to handle any additional initialization tasks.
     */
    ngAfterViewInit(): void {
        if (!this.dataSource) {
            return;
        }

        this.dataSource.sort = this.sort;
        this.dataSource.sortingDataAccessor = (data, sortHeadId) => {
            const element = data[sortHeadId];
            return element.sortValue || element.value || element.label || element.date;
        }
    }

    /**
     * A lifecycle hook that is called when any data-bound property of a directive changes. Define an ngOnChanges() method
     * to handle the changes.
     */
    ngOnChanges(): void {
        this.getContextData();
    }

    //
    // Context.
    //

    /**
     * Sets/updates the required attributes for the table to work.
     */
    getContextData(): void {
        // Table data not ready.
        if (!this.table) {
            return;
        }

        // Set context.
        this.columns = this.tableService.tableDataAsColumns(this.table);
        this.displayedColumns = this.tableService.getDisplayedColumnNames(this.columns, this.expandable);
        this.dataSource = this.tableService.createOrUpdateMatTableDataSource(this.table, this.dataSource);
    }

    /**
     * Returns the index of dataRow in this.dataSource.data
     * @param {Object} dataRow item in this.dataSource.data.
     */
    getDataRowIndex(dataRow: Object): number {
        return this.dataSource.data.indexOf(dataRow);
    }

    /**
     * Check if user exists in current selected users array.
     * @param {UserSearchResult} user
     * @returns {boolean}
     */
    isInSelectedValues(doc) {
      return this.selectedValues.some(userObj => userObj === doc);
    }

    //
    // Events.
    //

    /**
     * Update selected users array.
     * @param {MatCheckboxChange} event
     */
    updateSelectedValues(event: MatCheckboxChange) {
      const selectedValue = event.source.value;
      const isInSelectedValues = this.isInSelectedValues(selectedValue);
      if (event.checked && !isInSelectedValues) {
        this.selectedValues.push(selectedValue)
      } else if (!event.checked && isInSelectedValues) {
        const i = this.selectedValues.findIndex(userObj => userObj === selectedValue);
        this.selectedValues.splice(i, 1);
      }
      this.selectionOutput.emit(this.selectedValues);
    }

    /**
     * Gets called when a button is clicked, emits buttonOutput.
     * @param {string} columnName
     * @param {*} value
     */
    onButtonClick(columnName: string, value: any): void {
      if (columnName && value) {
          const output = {
              [columnName]: value
          }
          this.buttonOutput.emit(output as TableButtonClickEvent);
      }
    }

    /**
     * Gets called when an expand toggle is clicked.
     * @param {Object} dataRow item in this.dataSource.data.
     */
    onToggleClick(dataRow) {
      if (dataRow._expandData || dataRow._nestedTableData) {
        const key = this.getDataRowIndex(dataRow);
        this.expandedIndex = this.expandedIndex === key ? null : key;
      }
    }

    /**
     * Gets called when a nested button is clicked, emits buttonOutput.
     * @param {Object} event Output of (nested) onButtonClick().
     */
    onNestedButtonClick(event: Object): void {
        this.buttonOutput.emit(event as TableButtonClickEvent);
    }

    /**
     * Gets called when a row is clicked, emits tableOutput.
     * @param {*} value
     */
    onRowClick(value: any): void {
        if (value) {
            this.tableOutput.emit(value as any);
        }
    }

    /**
     * Gets called when a column is sorted.
     * @param {active: string, direction: 'asc' | 'desc'} event
     */
    onSort(event: { active: string, direction: 'asc' | 'desc' }): void {
        const output: TableSort = {
            value: event.active,
            order: event.direction,
        }
        this.sortOutput.emit(output as TableSortEvent);
    }

    /**
     * Gets called when a columns value is changed.
     * @param {ExtensiveCell} column
     * @param {Choice} choice
     */
      onColumnChanged(column: ExtensiveCell, choice: Choice) {
        column.onChange(choice);
      }
}
