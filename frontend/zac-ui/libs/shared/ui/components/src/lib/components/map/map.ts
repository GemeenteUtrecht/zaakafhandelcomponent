import {Geometry, Position} from '@gu/models';

export interface MapGeometry {
  geometry: Geometry,
  editable?: boolean
  title?: string,
  onClick?: Function,
  onChange?: Function
}

export interface MapMarker {
  coordinates: Position,
  editable?: boolean,
  iconAnchor?: number[],
  iconUrl?: string,
  iconSize?: number[],
  shadowAnchor?: number[],
  shadowUrl?: string,
  shadowSize?: number[],
  title?: string,
  onClick?: Function,
  onChange?: Function
}
