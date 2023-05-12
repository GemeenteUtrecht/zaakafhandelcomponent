import {Geometry} from '../geojson/geojson';
import {ObjectType} from '../objects/objecttype';
import { Zaak } from '../zaken/zaak';

export interface PaginatedZaakObjects {
  count: number,
  next: string,
  previous: string,
  results: ZaakObject[]
}

export interface ZaakObject {
  record: {
    correctedBy?: string
    correctionFor?: string
    data?: {
      [key: string]: string,
    }
    geometry?: Geometry | Geometry[],
    index?: number,
    registrationAt?: string,
    startAt: string,
    endAt?: string
    typeVersion: number,
  },
  type: ObjectType|string,
  url?: string
  uuid?: string,
  zaakobjectUrl?: string,
  stringRepresentation: string,
}

export interface ZaakObjectGroup {
  items: ZaakObject[]
  label: string,
  objectType: string,
}

export interface ZaakObjectRelation {
  object?: string,
  objectType: ObjectType,
  objectTypeOverige?: string,
  relatieOmschrijving?: string,
  url?: string,
  uuid?: string,
  zaak: string,
}
