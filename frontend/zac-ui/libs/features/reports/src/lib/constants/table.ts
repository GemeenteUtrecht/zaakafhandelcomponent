const tableHead =  ['Zaaknummer', 'Zaaktype', 'Startdatum', 'Omschrijving', 'Status']

const tableHeadMapping = {
  'Zaaknummer': 'identificatie',
  'Zaaktype': 'zaaktype.omschrijving',
  'Startdatum': 'startdatum',
  'Omschrijving': 'omschrijving',
  'Status': 'status'
}

export { tableHead, tableHeadMapping }
