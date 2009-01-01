# charset.py
"""Handle alternate character sets for character strings."""
#
# Copyright 2008, Darcy Mason
# This file is part of pydicom.
#
# pydicom is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# pydicom is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License (license.txt) for more details 


import logging
logger = logging.getLogger('pydicom')

# Map DICOM Specific Character Set to python equivalent
python_encoding = {
    '': 'iso8859',           # default character set for DICOM
    'ISO_IR 6': 'iso8859',   # alias for latin_1 too
    'ISO_IR 100': 'latin_1',
    'ISO 2022 IR 87': 'iso2022_jp',
    'ISO 2022 IR 13': 'iso2022_jp',  #XXX this mapping does not work on chrH32.dcm test files (but no others do either)
    'ISO 2022 IR 149': 'euc_kr',   # XXX chrI2.dcm -- does not quite work -- some chrs wrong. Need iso_ir_149 python encoding
    'ISO_IR 192': 'UTF8',     # from Chinese example, 2008 PS3.5 Annex J p1-4
    'GB18030': 'GB18030',
    'ISO_IR 126': 'iso_ir_126',  # Greek
    'ISO_IR 127': 'iso_ir_127',  # Arab
    'ISO_IR 138': 'iso_ir_138', # Hebrew
    'ISO_IR 144': 'iso_ir_144', # Russion
    }

from dicom.valuerep import PersonNameUnicode, PersonName

# PS3.5-2008 6.1.1 (p 18) says:
#   default is ISO-IR 6 G0, equiv to common chr set of ISO 8859 (PS3.5 6.1.2.1)
#    (0008,0005)  value 1 can *replace* the default encoding... 
#           for VRs of SH, LO, ST, LT, PN and UT (PS3.5 6.1.2.3)...
#           with a single-byte character encoding
#  if (0008,0005) is multi-valued, then value 1 (or default if blank)...
#           is used until code extension escape sequence is hit,
#          which can be at start of string, or after CR/LF, FF, or
#          in Person Name PN, after ^ or =
# NOTE also that 7.5.3 SEQUENCE INHERITANCE states that if (0008,0005) 
#       is not present in a sequence item then it is inherited from its parent.
def decode(data_element, dicom_character_set):
    """Apply the DICOM character encoding to the data element
    
    data_element -- DataElement instance containing a value to convert
    dicom_character_set -- the value of Specific Character Set (0008,0005),
                    which may be a single value,
                    a multiple value (code extension), or
                    may also be '' or None.
                    If blank or None, ISO_IR 6 is used.
    
    """
    if not dicom_character_set:
        dicom_character_set = ['ISO_IR 6']
    have_character_set_list = True
    try:
        dicom_character_set.append # check if is list-like object
    except AttributeError:
        have_character_set_list = False

    if have_character_set_list:
        if not dicom_character_set[0]:
            dicom_character_set[0] = "ISO_IR 6"
    else:
        dicom_character_set = [dicom_character_set]
    # decode the string value to unicode
    # PN is special case as may have 3 components with differenct chr sets
    if data_element.VR == "PN": 
        # logger.warn("%s ... type: %s" %(str(data_element), type(data_element.VR)))
        encodings = [python_encoding[x] for x in dicom_character_set]
        if len(encodings) == 1:
            encodings = [encodings[0]]*3
        if len(encodings) == 2:
            encodings.append(encodings[1])
        data_element.value = PersonNameUnicode(data_element.value, encodings)
    if data_element.VR in ['SH', 'LO', 'ST', 'LT', 'UT']:
        data_element.value = data_element.value.decode(python_encoding[dicom_character_set[0]])