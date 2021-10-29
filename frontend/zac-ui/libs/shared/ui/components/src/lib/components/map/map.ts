import {Geometry, Position} from '@gu/models';

export interface MapGeometry {
  geometry: Geometry,
  editable?: boolean
  onClick?: Function,
  onChange?: Function
}

export interface MapMarker {
  coordinates: Position,
  editable?: boolean
  onClick?: Function,
  onChange?: Function
}
