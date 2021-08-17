import {Geometry} from "./geojson/geojson";

export interface ZaakObject {
  record: {
    correctedBy?: string
    correctionFor?: string
    data?: {
      [key: string]: string,
    }
    geometry?: Geometry[],
    index?: number,
    registrationAt?: string,
    startAt: string,
    endAt?: string
    typeVersion: number,
  },
  type: string
  url?: string
  uuid?: string,
}
