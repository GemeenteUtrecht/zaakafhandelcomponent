export interface Table {
  headData: string[];
  tableData: RowData[];
}

export interface RowData {
  cellData: CellData;
  expandData?: string;
}

export interface CellData {
  [key: string]: string | ExtensiveCell
}

export interface ExtensiveCell {
  type: 'link' | 'icon' | 'button',
  value: string | number,
  url?: string
}
