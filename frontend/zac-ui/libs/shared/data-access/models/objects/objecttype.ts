export interface ObjectType {
  allowGeometry: boolean,
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
  versions: ObjectTypeVersion[] | string[],
}

export interface ObjectTypeVersion {
  createdAt: string,
  jsonSchema: JsonSchema,
  modifiedAt: string,
  objectType: string,
  publishedAt: string,
  status: string,
  url: string,
  version: number,
}

interface JsonSchema {
  default: object,
  description: string,
  examples: [],
  properties: object,
  required: [],
  title: string,
}
