const tableHead = ['Zaaknummer', 'Zaaktype', 'Omschrijving', 'Deadline']

const tableHeadMapping = {
  'zaaknummer': 'identificatie',
  'zaaktype': 'zaaktype.omschrijving',
  'omschrijving': 'omschrijving',
  'deadline': 'deadline'
}

export { tableHead, tableHeadMapping }
