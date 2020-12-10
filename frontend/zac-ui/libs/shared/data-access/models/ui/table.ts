export interface CellData {
  cellData: object;
  expandData: string;
}

export interface Table {
  headData: string[];
  elementData: CellData[];
}
