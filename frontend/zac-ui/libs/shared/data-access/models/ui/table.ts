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
  buttonInfo?: string;
  iconColor?: string;
  iconInfo?: string;
  label?: string | number;
  target?: '_blank' | '_parent' | '_self' | '_top' | string
  type: 'button' | 'chip' | 'icon' | 'link' | 'table' | 'text' | 'date';
  url?: string;
  value?: any;
  date?: string;
  sortValue?: any;
}

export interface TableSort {
  value: string;
  order: 'asc' | 'desc';
}

export interface Column {
  name: string,
  label: string,
}
