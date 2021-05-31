const tableHead =  ['Zaaknummer', 'Zaaktype', 'Startdatum', 'Omschrijving', 'Status']

const tableHeadMapping = {
  'Zaaknummer': 'identificatie',
  'Zaaktype': 'zaaktypeOmschrijving',
  'Startdatum': 'startdatum',
  'Omschrijving': 'omschrijving',
  'Status': 'status'
}

export { tableHead, tableHeadMapping }
