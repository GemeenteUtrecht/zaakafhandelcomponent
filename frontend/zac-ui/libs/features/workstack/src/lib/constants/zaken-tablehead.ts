const tableHead = [
  'Zaaknummer',
  'Omschrijving',
  'Zaaktype',
  'Startdatum',
  'Uiterste einddatum',
  'Vertrouwelijkheid'
]

const tableHeadMapping = {
  'Zaaknummer': 'identificatie',
  'Omschrijving': 'omschrijving',
  'Zaaktype': 'zaaktype.omschrijving',
  'Startdatum': 'startdatum',
  'Uiterste einddatum': 'einddatum',
  'Vertrouwelijkheid': 'vertrouwelijkheidaanduiding'
}

export { tableHead, tableHeadMapping }
