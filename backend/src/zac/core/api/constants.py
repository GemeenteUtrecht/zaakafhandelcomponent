import re

ACCEPTABLE_CONTENT_TYPES = {
    "CSV": "text/csv",
    "DOC": "application/msword",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "EML": "message/rfc822",
    "JPEG": "image/jpeg",
    "MBOX": "application/mbox",
    "MSG": "application/vnd.ms-outlook",
    "ODP": "application/vnd.oasis.opendocument.presentation",
    "ODS": "application/vnd.oasis.opendocument.spreadsheet",
    "ODT": "application/vnd.oasis.opendocument.text",
    "PDF": "application/pdf",
    "PNG": "image/png",
    "PPT": "application/vnd.ms-powerpoint",
    "PPTX": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "TXT": "text/plain",
    "TIFF": "image/tiff",
    "XLS": "application/vnd.ms-excel",
    "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

RE_PROG = re.compile(r"^[a-zA-Z0-9-_()\s]{1,245}\.[a-zA-Z0-9]{1,10}$")
