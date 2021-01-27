export interface Table {
  headData: string[];
  bodyData: RowData[];
}

export interface RowData {
  cellData: CellData;
  expandData?: string;
  clickOutput?: any;
}

export interface CellData {
  [key: string]: string | ExtensiveCell;
}

export interface ExtensiveCell {
  type: 'link' | 'icon' | 'button';
  value: string | number;
  url?: string;
  iconColor?: string;
}
