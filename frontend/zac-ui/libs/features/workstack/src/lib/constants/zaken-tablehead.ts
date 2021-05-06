const tableHead = [
  'Identificatie',
  'Zaaktype',
  'Startdatum',
  'Geplande einddatum',
  'Vertrouwelijkheid'
]

const tableHeadMapping = {
  'Identificatie': 'identificatie',
  'Zaaktype': 'zaaktype.omschrijving',
  'Startdatum': 'startdatum',
  'Geplande einddatum': 'einddatumGepland',
  'Vertrouwelijkheid': 'vertrouwelijkheidaanduiding'
}

export { tableHead, tableHeadMapping }
