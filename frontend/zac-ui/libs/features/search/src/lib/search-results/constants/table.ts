const tableHead = ['Zaaknummer', 'Zaaktype', 'Omschrijving', 'Deadline']

const tableHeadMapping = {
  'Zaaknummer': 'identificatie',
  'Zaaktype': 'zaaktype.omschrijving',
  'Omschrijving': 'omschrijving',
  'Deadline': 'deadline'
}

export { tableHead, tableHeadMapping }
