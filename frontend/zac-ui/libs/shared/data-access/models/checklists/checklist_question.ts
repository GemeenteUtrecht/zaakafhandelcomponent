export interface QuestionChoice {
  name: string,
  value: string,
}

export interface ChecklistQuestion {
  question: string,
  order: number,
  choices: QuestionChoice[],
  isMultipleChoice: boolean
}
