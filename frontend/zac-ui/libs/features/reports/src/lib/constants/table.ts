const tableHead =  ['Zaaknummer', 'Zaaktype', 'Datum', 'Status', 'Toelichting']

const tableHeadMapping = {
  'zaaknummer': 'identificatie',
  'zaaktype': 'zaaktype.omschrijving',
  'startdatum': 'startdatum',
  'status': 'status',
  'toelichting': 'omschrijving'
}

export { tableHead, tableHeadMapping }
