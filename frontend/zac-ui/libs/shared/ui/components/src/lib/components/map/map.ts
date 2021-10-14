import {Position} from '@gu/models';

export interface MapMarker {
  coordinates: Position,
  onClick: Function,
}
