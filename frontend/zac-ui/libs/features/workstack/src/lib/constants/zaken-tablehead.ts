const tableHead = [
  'Identificatie',
  'Zaaktype',
  'Startdatum',
  'Uiterste einddatum',
  'Vertrouwelijkheid'
]

const tableHeadMapping = {
  'Identificatie': 'identificatie',
  'Zaaktype': 'zaaktype.omschrijving',
  'Startdatum': 'startdatum',
  'Uiterste einddatum': 'deadline',
  'Vertrouwelijkheid': 'vertrouwelijkheidaanduiding'
}

export { tableHead, tableHeadMapping }
