"""Lectura segura de CSV y XLSX: límites de tamaño, filas y zip; solo valores (sin fórmulas)."""
import csv
import io
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from modules.data_import.domain.errors import ImportValidationError

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 2000
MAX_COLUMNS = 60
MAX_UNCOMPRESSED = 50 * 1024 * 1024
MAX_ZIP_ENTRIES = 200
MAX_CELL = 500


@dataclass(frozen=True)
class ParsedFile:
    headers: list[str]
    rows: list[list[str]]


def _fail(message: str) -> ImportValidationError:
    return ImportValidationError({'file': [message]})


def parse_upload(filename: str, content: bytes) -> ParsedFile:
    name = (filename or '').lower()
    if len(content) == 0:
        raise _fail('El archivo está vacío.')
    if len(content) > MAX_BYTES:
        raise _fail('El archivo supera el máximo de 5 MB.')
    if name.endswith('.csv'):
        parsed = _parse_csv(content)
    elif name.endswith('.xlsx'):
        parsed = _parse_xlsx(content)
    else:
        raise _fail('Formato no admitido: sube un archivo .csv o .xlsx.')
    return _finish(parsed)


def _finish(parsed: ParsedFile) -> ParsedFile:
    headers = [h.strip() for h in parsed.headers]
    while headers and not headers[-1]:
        headers.pop()
    if not headers:
        raise _fail('El archivo no tiene cabeceras en la primera fila.')
    if len(headers) > MAX_COLUMNS:
        raise _fail(f'El archivo tiene demasiadas columnas (máximo {MAX_COLUMNS}).')
    headers = [h or f'Columna {i}' for i, h in enumerate(headers, start=1)]
    if len({h.lower() for h in headers}) != len(headers):
        raise _fail('Hay cabeceras repetidas: cada columna debe tener un nombre distinto.')
    rows = [[(c or '')[:MAX_CELL] for c in (row + [''] * len(headers))[:len(headers)]] for row in parsed.rows]
    rows = [row for row in rows if any(cell.strip() for cell in row)]
    if not rows:
        raise _fail('El archivo no tiene filas de datos.')
    if len(rows) > MAX_ROWS:
        raise _fail(f'El archivo supera el máximo de {MAX_ROWS} filas de datos.')
    return ParsedFile(headers, rows)


def _decode(content: bytes) -> str:
    for encoding in ('utf-8-sig', 'cp1252'):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode('latin-1')


def _parse_csv(content: bytes) -> ParsedFile:
    text = _decode(content)
    first_line = next((line for line in text.splitlines() if line.strip()), '')
    delimiter = max(',;\t', key=first_line.count) if first_line else ','
    try:
        records = [row for row in csv.reader(io.StringIO(text), delimiter=delimiter) if any(c.strip() for c in row)]
    except csv.Error as exc:
        raise _fail(f'El CSV no se pudo leer: {exc}') from exc
    if not records:
        raise _fail('El archivo está vacío.')
    return ParsedFile(records[0], records[1:MAX_ROWS + 2])


def _cell(value: object) -> str:
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, float):
        return format(Decimal(repr(value)), 'f')
    return str(value)


def _parse_xlsx(content: bytes) -> ParsedFile:
    if not content.startswith(b'PK'):
        raise _fail('El archivo .xlsx no es válido.')
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ZIP_ENTRIES or sum(i.file_size for i in infos) > MAX_UNCOMPRESSED:
                raise _fail('El archivo .xlsx es demasiado grande o tiene demasiadas partes.')
    except zipfile.BadZipFile as exc:
        raise _fail('El archivo .xlsx está dañado.') from exc
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl lanza tipos varios ante archivos dañados
        raise _fail('El archivo .xlsx no se pudo leer.') from exc
    try:
        sheet = workbook.worksheets[0]
        records: list[list[str]] = []
        for raw in sheet.iter_rows(values_only=True):
            row = [_cell(c) for c in raw]
            if any(c.strip() for c in row):
                records.append(row)
            if len(records) > MAX_ROWS + 1:
                break
    finally:
        workbook.close()
    if not records:
        raise _fail('El archivo está vacío.')
    return ParsedFile(records[0], records[1:])


TEMPLATE_CSV = (
    'fecha,n_venta,producto,cantidad,precio_unitario,cliente,metodo_pago,canal,proveedor,costo_unitario,notas\r\n'
    '15/10/2026,V-001,Café molido 250 g,2,35.00,Ana Pérez,efectivo,tienda,Distribuidora Andina,22.50,\r\n'
    '15/10/2026,V-001,Taza cerámica,1,28.00,Ana Pérez,efectivo,tienda,Distribuidora Andina,15.00,\r\n'
    '16/10/2026,V-002,Café molido 250 g,1,35.00,,qr,whatsapp,,,\r\n'
)
