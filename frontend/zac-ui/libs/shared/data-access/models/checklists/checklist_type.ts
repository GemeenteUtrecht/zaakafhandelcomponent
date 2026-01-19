import {ChecklistQuestion} from './checklist_question';

export interface ChecklistType {
  uuid: string,
  created: string,
  modified: string,
  questions: ChecklistQuestion[]
  zaaktype: string,
  zaaktype_catalogus: string,
  zaaktype_identificatie: string,
}
