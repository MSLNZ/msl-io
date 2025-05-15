##
# <p>Copyright (c) 2006-2012 Stephen John Machin, Lingfo Pty Ltd</p>
# <p>This module is part of the xlrd package, which is released under a BSD-style licence.</p>
##

BYTES_LITERAL = lambda x: x.encode('latin1')
UNICODE_LITERAL = lambda x: x
BYTES_ORD = lambda byte: byte
from io import BytesIO as BYTES_IO
def fprintf(f, fmt, *vargs):
    fmt = fmt.replace("%r", "%a")
    if fmt.endswith('\n'):
        print(fmt[:-1] % vargs, file=f)
    else:
        print(fmt % vargs, end=' ', file=f)
EXCEL_TEXT_TYPES = (str, bytes, bytearray) # xlwt: isinstance(obj, EXCEL_TEXT_TYPES)
REPR = ascii
unicode = lambda b, enc: b.decode(enc)
ensure_unicode = lambda s: s
unichr = chr
