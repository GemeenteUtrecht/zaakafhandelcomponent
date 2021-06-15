interface JsonSchema {
title: string,
default: object,
examples: [],
required: [],
properties: object,
description: string,
}

interface Version {
    url: string,
    version: number,
    objectType: string,
    status: string,
    jsonSchema: JsonSchema,
    createdAt: string,
    modifiedAt: string,
    publishedAt: string,
}

interface Objecttype {
  url: string,
  uuid: string,
  name: string,
  namePlural: string,
  description: string,
  dataClassification: string,
  maintainerOrganization: string,
  maintainerDepartment: string,
  contactPerson: string,
  contactEmail: string,
  source: string,
  updateFrequency: string,
  providerOrganization: string,
  documentationUrl: string,
  labels: object,
  createdAt: string,
  modifiedAt: string,
  versions: Version[],
}

interface Record {
  index: number,
  typeVersion: number,
  data: object,
  geometry: object,
  startAt: string,
  endAt: string,
  registrationAt: string,
  correctionFor: number,
  correctedBy: string
}

interface GerelateerdeObject {
  url: string,
  uuid: string,
  type: Objecttype,
  record: Record
}

interface GroupGerelateerdeObjecten {
  objectType: string,
  label: string,
  items: Array<GerelateerdeObject>
}

export {GroupGerelateerdeObjecten, GerelateerdeObject};
