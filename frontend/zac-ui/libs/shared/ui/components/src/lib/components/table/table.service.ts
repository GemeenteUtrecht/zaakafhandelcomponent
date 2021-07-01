import {Injectable} from '@angular/core';
import {MatTableDataSource} from '@angular/material/table';
import {Column, ExtensiveCell, RowData, Table} from '@gu/models';


@Injectable()
export class TableService {

  //
  // MatTableDataSource
  //

  /**
   * Creates/updates MatTableDataSource based on table.
   * @param {Table} table
   * @param {MatTableDataSource} [dataSource] updates if given, creates if omitted.
   * @return {MatTableDataSource}
   */
  createOrUpdateMatTableDataSource(table: Table, dataSource: MatTableDataSource<any> = null): MatTableDataSource<any> {
    if (dataSource) {
      dataSource.data = this.tableDataAsMatTableDataSourceData(table);
      return dataSource;
    }
    return this.tableDataAsMatTableDataSource(table);
  }

  /**
   * Converts a Table to a MatTableDataSource.
   * @param {Table} table
   * @return {MatTableDataSource}
   */
  tableDataAsMatTableDataSource(table: Table): MatTableDataSource<any> {
    const data = this.tableDataAsMatTableDataSourceData(table);
    return new MatTableDataSource(data);
  }

  /**
   * Converts a Table to a MatTableDataSource data.
   * @param {Table} table
   * @return {Object[]}
   */
  tableDataAsMatTableDataSourceData(table: Table): Object[] {
    const columns: { name: string, label: string }[] = this.tableDataAsColumns(table)
    return table.bodyData.map((rowData: RowData): Object =>
      Object.entries(rowData.cellData).reduce((acc: Object, [key, cell], index) => {
        acc[columns[index].name] = this.cellAsExtensiveCell(cell);
        acc['_expandData'] = rowData.expandData;
        acc['_nestedTableData'] = rowData.nestedTableData;
        acc['_clickOutput'] = rowData.clickOutput;
        return acc
      }, {}));
  }

  //
  // Columns
  //

  /**
   * Returns the configured columns in tableData.
   * @param {Table} table
   * @return {Column[]}
   */
  tableDataAsColumns(table: Table): Column[] {
    return table.headData.map((value: string, index: number) => {
      const name = this.getColumnName(table, index)

      if (value) {
        return {name: name, label: value};
      }

      return {name: name, label: ''};
    });
  }

  /**
   * Returns the name of a column, either by key of CellData at position index or index.
   * @param {Table} table
   * @param {number} index
   * @return string
   */
  getColumnName(table, index) {
    return String(
        table.bodyData.length && Object.keys(table.bodyData[0].cellData).length
          ? Object.keys(table.bodyData[0].cellData)[index]
          : index
      );
  }

  /**
   * Returns the names of all columns that should be shown in table.
   * @param {Column[]} columns
   * @param {boolean} expandable Whether the table should be expandable (add column).
   * @return {string[]}
   */
  getDisplayedColumnNames(columns: Column[], expandable = false): string[] {
    const uiColumns = expandable ? [{name: '_expandableToggle', label: ''}] : [];
    return [...uiColumns, ...columns].map(c => c.name);
  }

  //
  // Legacy data transforms.
  // TODO: Consider migrating to a new table format?
  //

  /**
   * Returns cell as ExtensiveCell.
   * @param {string | ExtensiveCell} cell
   * @return {ExtensiveCell}
   */
  cellAsExtensiveCell(cell: string | ExtensiveCell): ExtensiveCell {
    // cell is string, create ExtensiveCell.
    if (!this.getExtensiveCellType(cell)) {
      return {
        label: cell as string,
        type: 'text',
      }
    }

    // cell is ExtensiveCell.
    return cell as ExtensiveCell;
  }

  /**
   * Returns the cell type if value is ExtensiveCell, return "null" if value is a string (not ExtensiveCell).
   * @param {ExtensiveCell | string} value
   * @return {string|null}
   */
  getExtensiveCellType(value: ExtensiveCell | string): string | null {
    if (!!value) {
      if (typeof value === 'object') {
        return value.type;
      }
    }
    return null;
  }
}
