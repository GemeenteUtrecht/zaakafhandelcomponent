import {Geometry, Position} from '@gu/models';

export interface MapGeometry {
  geometry: Geometry,
  actions?: MapAction[],
  editable?: boolean
  title?: string,
  contentProperties?: [string, string][],
  onClick?: Function,
  onChange?: Function

}

export interface MapMarker {
  coordinates: Position,
  actions?: MapAction[],
  editable?: boolean,
  iconAnchor?: number[],
  iconUrl?: string,
  iconSize?: number[],
  shadowAnchor?: number[],
  shadowUrl?: string,
  shadowSize?: number[],
  title?: string,
  contentProperties?: [string, string][],
  onClick?: Function,
  onChange?: Function
}

export interface MapAction {
  label: string,
  onClick: Function,
}
