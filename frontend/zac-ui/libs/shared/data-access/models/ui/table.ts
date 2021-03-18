export interface Table {
  headData: string[];
  bodyData: RowData[];
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
