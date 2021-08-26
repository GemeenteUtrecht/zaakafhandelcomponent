import {Geometry} from "../geojson/geojson";

interface JsonSchema {
  default: object,
  description: string,
  examples: [],
  properties: object,
  required: [],
  title: string,
}

export interface Version {
  createdAt: string,
  jsonSchema: JsonSchema,
  modifiedAt: string,
  objectType: string,
  publishedAt: string,
  status: string,
  url: string,
  version: number,
}

export interface ObjectType {
  contactEmail: string,
  contactPerson: string,
  createdAt: string,
  dataClassification: string,
  description: string,
  documentationUrl: string,
  labels: object,
  maintainerDepartment: string,
  maintainerOrganization: string,
  modifiedAt: string,
  name: string,
  namePlural: string,
  providerOrganization: string,
  source: string,
  updateFrequency: string,
  url: string,
  uuid: string,
  versions: Version[],
}

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
  type: ObjectType|string,
  url?: string
  uuid?: string,
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
