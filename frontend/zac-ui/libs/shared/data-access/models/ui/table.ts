// @ts-ignore
import {Choice} from '../../../ui/components/src';

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
  type: 'button' | 'chip' | 'icon' | 'link' | 'select' | 'table' | 'text' | 'date' | 'checkbox';
  url?: string;
  value?: any;
  date?: string;
  sortValue?: any;

  error?: string;

  checked?: boolean;

  style?: 'no-minwidth'

  /** @type {Function} When type is "select", an onChange callback can be specified. */
  choices? : Choice[]

  /** @type {Function} When type is "select", an onChange callback can be specified. */
  onChange? : Function
}

export interface TableSort {
  value: string;
  order: 'asc' | 'desc';
}

export interface Column {
  name: string,
  label: string,
}
