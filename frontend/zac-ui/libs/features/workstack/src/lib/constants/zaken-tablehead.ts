const zakenTableHead = [
  'Zaaknummer',
  'Omschrijving',
  'Zaaktype',
  'Status',
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

export { zakenTableHead }
