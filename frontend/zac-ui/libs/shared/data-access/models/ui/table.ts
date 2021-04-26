export class Table {
  headData: string[];
  bodyData: RowData[];

  constructor(
    headData: string[],
    bodyData: RowData[]
  ) {
    this.headData = headData;
    this.bodyData = bodyData;
  }
}

export interface RowData {
  cellData: CellData;
  expandData?: string;
  nestedTableData?: Table;
  clickOutput?: any;
}

export interface CellData {
  [key: string]: string | ExtensiveCell;
}

export interface ExtensiveCell {
  type: 'link' | 'icon' | 'button' | 'table';
  label?: string | number;
  url?: string;
  value?: string;
  iconColor?: string;
  buttonType?: string;
}

export interface TableSort {
  value: string;
  order: 'asc' | 'desc';
}
