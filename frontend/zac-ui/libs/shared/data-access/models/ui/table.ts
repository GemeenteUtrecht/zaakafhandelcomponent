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
  buttonType?: string;
  iconColor?: string;
  label?: string | number;
  target?: '_blank'|'_parent'|'_self'|'_top'|string
  type: 'link' | 'icon' | 'button' | 'table';
  url?: string;
  value?: any;
}

export interface TableSort {
  value: string;
  order: 'asc' | 'desc';
}
