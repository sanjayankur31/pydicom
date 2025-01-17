# -*- coding: utf-8 -*-
# Copyright 2008-2018 pydicom authors. See LICENSE file for details.
"""Unit tests for the pydicom.charset module."""

import pytest

import pydicom.charset
from pydicom import dcmread, config
from pydicom.data import get_charset_files, get_testdata_files
from pydicom.dataelem import DataElement
from pydicom.filebase import DicomBytesIO

# The file names (without '.dcm' extension) of most of the character test
# files, together with the respective decoded PatientName tag values.
# Most of these (except the Korean file) are taken from David Clunie's
# charset example files.
FILE_PATIENT_NAMES = [
    ('chrArab', u'قباني^لنزار'),
    ('chrFren', u'Buc^Jérôme'),
    ('chrFrenMulti', u'Buc^Jérôme'),
    ('chrGerm', u'Äneas^Rüdiger'),
    ('chrGreek', u'Διονυσιος'),
    ('chrH31', u'Yamada^Tarou=山田^太郎=やまだ^たろう'),
    ('chrH32', u'ﾔﾏﾀﾞ^ﾀﾛｳ=山田^太郎=やまだ^たろう'),
    ('chrHbrw', u'שרון^דבורה'),
    ('chrI2', u'Hong^Gildong=洪^吉洞=홍^길동'),
    ('chrJapMulti', u'やまだ^たろう'),
    ('chrJapMultiExplicitIR6', u'やまだ^たろう'),
    ('chrKoreanMulti', u'김희중'),
    ('chrRuss', u'Люкceмбypг'),
    ('chrX1', u'Wang^XiaoDong=王^小東'),
    ('chrX2', u'Wang^XiaoDong=王^小东'),
]

# Test data for all single-byte coding extensions.
# Mostly taken from the same example files.
ENCODED_NAMES = [
    ('ISO 2022 IR 13', u'ﾔﾏﾀﾞ^ﾀﾛｳ',
     b'\x1b\x29\x49\xd4\xcf\xc0\xde\x5e\xc0\xdb\xb3'),
    ('ISO 2022 IR 100', u'Buc^Jérôme',
     b'\x1b\x2d\x41\x42\x75\x63\x5e\x4a\xe9\x72\xf4\x6d\x65'),
    ('ISO 2022 IR 101', u'Wałęsa',
     b'\x1b\x2d\x42\x57\x61\xb3\xea\x73\x61'),
    ('ISO 2022 IR 109', u'antaŭnomo',
     b'\x1b\x2d\x43\x61\x6e\x74\x61\xfd\x6e\x6f\x6d\x6f'),
    ('ISO 2022 IR 110', u'vārds',
     b'\x1b\x2d\x44\x76\xe0\x72\x64\x73'),
    ('ISO 2022 IR 127', u'قباني^لنزار',
     b'\x1b\x2d\x47\xe2\xc8\xc7\xe6\xea\x5e\xe4\xe6\xd2\xc7\xd1'),
    ('ISO 2022 IR 126', u'Διονυσιος',
     b'\x1b\x2d\x46\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2'),
    ('ISO 2022 IR 138', u'שרון^דבורה',
     b'\x1b\x2d\x48\xf9\xf8\xe5\xef\x5e\xe3\xe1\xe5\xf8\xe4'),
    ('ISO 2022 IR 144', u'Люкceмбypг',
     b'\x1b\x2d\x4c\xbb\xee\xda\x63\x65\xdc\xd1\x79\x70\xd3'),
    ('ISO 2022 IR 148', u'Çavuşoğlu',
     b'\x1b\x2d\x4d\xc7\x61\x76\x75\xfe\x6f\xf0\x6c\x75'),
    ('ISO 2022 IR 166', u'นามสกุล',
     b'\x1b\x2d\x54\xb9\xd2\xc1\xca\xa1\xd8\xc5'),
]


class TestCharset(object):
    def teardown(self):
        config.enforce_valid_values = False

    def test_encodings(self):
        test_string = u'Hello World'
        for x in pydicom.charset.python_encoding.items():
            test_string.encode(x[1])

    def test_nested_character_sets(self):
        """charset: can read and decode SQ with different encodings........."""
        ds = dcmread(get_charset_files("chrSQEncoding.dcm")[0])
        ds.decode()

        # These datasets inside of the SQ cannot be decoded with
        # default_encoding OR UTF-8 (the parent dataset's encoding).
        # Instead, we make sure that it is decoded using the
        # (0008,0005) tag of the dataset

        sequence = ds[0x32, 0x1064][0]
        assert ['shift_jis', 'iso2022_jp'] == sequence._character_set
        assert u'ﾔﾏﾀﾞ^ﾀﾛｳ=山田^太郎=やまだ^たろう' == sequence.PatientName

    def test_inherited_character_set_in_sequence(self):
        """charset: can read and decode SQ with parent encoding............."""
        ds = dcmread(get_charset_files('chrSQEncoding1.dcm')[0])
        ds.decode()

        # These datasets inside of the SQ shall be decoded with the parent
        # dataset's encoding
        sequence = ds[0x32, 0x1064][0]
        assert ['shift_jis', 'iso2022_jp'] == sequence._character_set
        assert u'ﾔﾏﾀﾞ^ﾀﾛｳ=山田^太郎=やまだ^たろう' == sequence.PatientName

    def test_standard_file(self):
        """charset: can read and decode standard file without special char.."""
        ds = dcmread(get_testdata_files("CT_small.dcm")[0])
        ds.decode()
        assert u'CompressedSamples^CT1' == ds.PatientName

    def test_invalid_character_set(self):
        """charset: replace invalid encoding with default encoding"""
        ds = dcmread(get_testdata_files("CT_small.dcm")[0])
        ds.read_encoding = None
        ds.SpecificCharacterSet = 'Unsupported'
        with pytest.warns(UserWarning,
                          match=u"Unknown encoding 'Unsupported' "
                                u"- using default encoding instead"):
            ds.decode()
            assert u'CompressedSamples^CT1' == ds.PatientName

    def test_invalid_character_set_enforce_valid(self):
        """charset: raise on invalid encoding"""
        config.enforce_valid_values = True
        ds = dcmread(get_testdata_files("CT_small.dcm")[0])
        ds.read_encoding = None
        ds.SpecificCharacterSet = 'Unsupported'
        with pytest.raises(LookupError,
                           match=u"Unknown encoding 'Unsupported'"):
            ds.decode()

    def test_decoding_with_specific_tags(self):
        """Decoding is correctly applied even if  Specific Character Set
        is not in specific tags..."""
        rus_file = get_charset_files("chrRuss.dcm")[0]
        ds = dcmread(rus_file, specific_tags=['PatientName'])
        ds.decode()
        assert 2 == len(ds)  # specific character set is always decoded
        assert u'Люкceмбypг' == ds.PatientName

    def test_bad_charset(self):
        """Test bad charset defaults to ISO IR 6"""
        # Python 3: elem.value is PersonName3, Python 2: elem.value is str
        elem = DataElement(0x00100010, 'PN', 'CITIZEN')
        pydicom.charset.decode_element(elem, ['ISO 2022 IR 126'])
        # After decode Python 2: elem.value is PersonNameUnicode
        assert 'iso_ir_126' in elem.value.encodings
        assert 'iso8859' not in elem.value.encodings
        # default encoding is iso8859
        pydicom.charset.decode_element(elem, [])
        assert 'iso8859' in elem.value.encodings

    def test_bad_encoded_single_encoding(self):
        """Test handling bad encoding for single encoding"""
        elem = DataElement(0x00100010, 'PN',
                           b'\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2')

        with pytest.warns(UserWarning, match="Failed to decode byte string "
                                             "with encoding 'UTF8'"):
            pydicom.charset.decode_element(elem, ['ISO_IR 192'])
            assert u'���������' == elem.value

    def test_bad_encoded_single_encoding_enforce_standard(self):
        """Test handling bad encoding for single encoding if
        config.enforce_valid_values is set"""
        config.enforce_valid_values = True
        elem = DataElement(0x00100010, 'PN',
                           b'\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2')
        msg = ("'utf.?8' codec can't decode byte 0xc4 in position 0: "
               "invalid continuation byte")
        with pytest.raises(UnicodeDecodeError, match=msg):
            pydicom.charset.decode_element(elem, ['ISO_IR 192'])

    def test_code_extensions_not_allowed(self):
        """Test that UTF8 does not allow code extensions"""
        elem = DataElement(0x00100010, 'PN', b'Buc^J\xc3\xa9r\xc3\xb4me')

        msg = ("Value 'ISO_IR 192' for Specific Character Set does not "
               "allow code extensions, ignoring: ISO 2022 IR 100, "
               "ISO 2022 IR 144")
        with pytest.warns(UserWarning, match=msg):
            pydicom.charset.decode_element(
                elem,
                ['ISO_IR 192', 'ISO 2022 IR 100', 'ISO 2022 IR 144']
            )
            assert u'Buc^Jérôme' == elem.value

    def test_convert_encodings_warnings(self):
        """Test warning if stand-alone encodings are used as code extension"""
        with pytest.warns(UserWarning, match="Value 'GBK' cannot be used as "
                                             "code extension, ignoring it"):
            encodings = pydicom.charset.convert_encodings(
                ['ISO_IR 126', 'GBK', 'ISO 2022 IR 144', 'ISO_IR 192'])
            assert ['iso_ir_126', 'iso_ir_144'] == encodings

    def test_convert_python_encodings(self):
        """Test that unknown encodings are returned unchanged by
        `convert_encodings`"""
        encodings = ['iso_ir_126', 'iso_ir_144']
        assert encodings == pydicom.charset.convert_encodings(encodings)

    def test_bad_decoded_multi_byte_encoding(self):
        """Test handling bad encoding for single encoding"""
        elem = DataElement(0x00100010, 'PN',
                           b'\x1b$(D\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2')

        with pytest.warns(UserWarning, match='Failed to decode byte string '
                                             'with encodings: iso-2022-jp'):
            pydicom.charset.decode_element(elem, ['ISO 2022 IR 159'])
            assert u'����������' == elem.value

    def test_bad_decoded_multi_byte_encoding_enforce_standard(self):
        """Test handling bad encoding for single encoding if
        `config.enforce_valid_values` is set"""
        config.enforce_valid_values = True
        elem = DataElement(0x00100010, 'PN',
                           b'\x1b$(D\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2')
        msg = ("'iso2022_jp' codec can't decode bytes in position 0-3: "
               "illegal multibyte sequence")
        with pytest.raises(UnicodeDecodeError, match=msg):
            pydicom.charset.decode_element(elem, ['ISO 2022 IR 159'])

    def test_unknown_escape_sequence(self):
        """Test handling bad encoding for single encoding"""
        elem = DataElement(0x00100010, 'PN',
                           b'\x1b\x2d\x46\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2')

        with pytest.warns(UserWarning, match='Found unknown escape sequence '
                                             'in encoded string value'):
            pydicom.charset.decode_element(elem, ['ISO_IR 100'])
            assert u'\x1b-FÄéïíõóéïò' == elem.value

    def test_unknown_escape_sequence_enforce_standard(self):
        """Test handling bad encoding for single encoding if
        `config.enforce_valid_values` is set"""
        config.enforce_valid_values = True
        elem = DataElement(0x00100010, 'PN',
                           b'\x1b\x2d\x46\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2')
        with pytest.raises(ValueError, match='Found unknown escape sequence '
                                             'in encoded string value'):
            pydicom.charset.decode_element(elem, ['ISO_IR 100'])

    def test_patched_charset(self):
        """Test some commonly misspelled charset values"""
        elem = DataElement(0x00100010, 'PN', b'Buc^J\xc3\xa9r\xc3\xb4me')
        pydicom.charset.decode_element(elem, ['ISO_IR 192'])
        # correct encoding
        assert u'Buc^Jérôme' == elem.value

        # patched encoding shall behave correctly, but a warning is issued
        elem = DataElement(0x00100010, 'PN', b'Buc^J\xc3\xa9r\xc3\xb4me')
        with pytest.warns(UserWarning,
                          match='Incorrect value for Specific Character Set '
                                "'ISO IR 192' - assuming 'ISO_IR 192'"):
            pydicom.charset.decode_element(elem, ['ISO IR 192'])
            assert u'Buc^Jérôme' == elem.value

        elem = DataElement(0x00100010, 'PN', b'Buc^J\xe9r\xf4me')
        with pytest.warns(UserWarning,
                          match='Incorrect value for Specific Character Set '
                                "'ISO-IR 144' - assuming 'ISO_IR 144'") as w:
            pydicom.charset.decode_element(elem, ['ISO_IR 100', 'ISO-IR 144'])
            # make sure no warning is issued for the correct value
            assert 1 == len(w)

        # not patched incorrect encoding is replaced by default encoding
        elem = DataElement(0x00100010, 'PN', b'Buc^J\xc3\xa9r\xc3\xb4me')
        with pytest.warns(UserWarning,
                          match=u"Unknown encoding 'ISOIR 192' - "
                                u"using default encoding instead"):
            pydicom.charset.decode_element(elem, ['ISOIR 192'])

        # Python encoding also can be used directly
        elem = DataElement(0x00100010, 'PN', b'Buc^J\xc3\xa9r\xc3\xb4me')
        pydicom.charset.decode_element(elem, ['utf8'])
        assert u'Buc^Jérôme' == elem.value

    def test_patched_code_extension_charset(self):
        """Test some commonly misspelled charset values for code extensions."""
        elem = DataElement(0x00100010, 'PN',
                           b'Dionysios=\x1b\x2d\x46'
                           b'\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2')
        # correct encoding
        pydicom.charset.decode_element(
            elem, ['ISO 2022 IR 100', 'ISO 2022 IR 126']
        )
        assert u'Dionysios=Διονυσιος' == elem.value

        # patched encoding shall behave correctly, but a warning is issued
        with pytest.warns(UserWarning,
                          match='Incorrect value for Specific Character Set '
                                "'ISO_2022-IR 100' - assuming "
                                "'ISO 2022 IR 100'"):
            elem = DataElement(0x00100010, 'PN',
                               b'Dionysios=\x1b\x2d\x46'
                               b'\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2')
            pydicom.charset.decode_element(elem,
                                   ['ISO_2022-IR 100', 'ISO 2022 IR 126'])
            assert u'Dionysios=Διονυσιος' == elem.value

        with pytest.warns(UserWarning,
                          match=r'Incorrect value for Specific Character Set '
                                r"'ISO_2022_IR\+126' - assuming "
                                r"'ISO 2022 IR 126'"):
            elem = DataElement(0x00100010, 'PN',
                               b'Dionysios=\x1b\x2d\x46'
                               b'\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2')
            pydicom.charset.decode_element(elem,
                                   ['ISO 2022 IR 100', 'ISO_2022_IR+126'])
            assert u'Dionysios=Διονυσιος' == elem.value

    def test_multi_charset_default_value(self):
        """Test that the first value is used if no escape code is given"""
        # regression test for #707
        elem = DataElement(0x00100010, 'PN', b'Buc^J\xe9r\xf4me')
        pydicom.charset.decode_element(
            elem, ['ISO 2022 IR 100', 'ISO 2022 IR 144']
        )
        assert u'Buc^Jérôme' == elem.value

        elem = DataElement(0x00081039, 'LO', b'R\xf6ntgenaufnahme')
        pydicom.charset.decode_element(
            elem, ['ISO 2022 IR 100', 'ISO 2022 IR 144']
        )
        assert u'Röntgenaufnahme' == elem.value

    def test_single_byte_multi_charset_personname(self):
        # component groups with different encodings
        elem = DataElement(0x00100010, 'PN',
                           b'Dionysios=\x1b\x2d\x46'
                           b'\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2')
        pydicom.charset.decode_element(
            elem, ['ISO 2022 IR 100', 'ISO 2022 IR 126']
        )
        assert u'Dionysios=Διονυσιος' == elem.value

        # multiple values with different encodings
        encoded = (b'Buc^J\xe9r\xf4me\\\x1b\x2d\x46'
                   b'\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2\\'
                   b'\x1b\x2d\x4C'
                   b'\xbb\xee\xda\x63\x65\xdc\xd1\x79\x70\xd3')
        elem = DataElement(0x00100060, 'PN', encoded)
        pydicom.charset.decode_element(elem, ['ISO 2022 IR 100',
                                      'ISO 2022 IR 144',
                                      'ISO 2022 IR 126'])
        assert [u'Buc^Jérôme', u'Διονυσιος', u'Люкceмбypг'] == elem.value

    def test_single_byte_multi_charset_text(self):
        # changed encoding inside the string
        elem = DataElement(0x00081039, 'LO',
                           b'Dionysios is \x1b\x2d\x46'
                           b'\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2')
        pydicom.charset.decode_element(
            elem, ['ISO 2022 IR 100', 'ISO 2022 IR 126']
        )
        assert u'Dionysios is Διονυσιος' == elem.value

        # multiple values with different encodings
        elem = DataElement(0x00081039, 'LO',
                           b'Buc^J\xe9r\xf4me\\\x1b\x2d\x46'
                           b'\xc4\xe9\xef\xed\xf5\xf3\xe9\xef\xf2\\'
                           b'\x1b\x2d\x4C'
                           b'\xbb\xee\xda\x63\x65\xdc\xd1\x79\x70\xd3')
        pydicom.charset.decode_element(elem, ['ISO 2022 IR 100',
                                      'ISO 2022 IR 144',
                                      'ISO 2022 IR 126'])
        assert [u'Buc^Jérôme', u'Διονυσιος', u'Люкceмбypг'] == elem.value

    @pytest.mark.parametrize('encoding, decoded, raw_data', ENCODED_NAMES)
    def test_single_byte_code_extensions(self, encoding, decoded, raw_data):
        # single-byte encoding as code extension
        elem = DataElement(0x00081039, 'LO', b'ASCII+' + raw_data)
        pydicom.charset.decode_element(elem, ['', encoding])
        assert u'ASCII+' + decoded == elem.value

    @pytest.mark.parametrize('filename, patient_name', FILE_PATIENT_NAMES)
    def test_charset_patient_names(self, filename, patient_name):
        """Test patient names are correctly decoded and encoded."""
        # check that patient names are correctly read
        file_path = get_charset_files(filename + '.dcm')[0]
        ds = dcmread(file_path)
        ds.decode()
        assert patient_name == ds.PatientName

        # check that patient names are correctly written back
        fp = DicomBytesIO()
        fp.is_implicit_VR = False
        fp.is_little_endian = True
        ds.save_as(fp, write_like_original=False)
        fp.seek(0)
        ds = dcmread(fp)
        assert patient_name == ds.PatientName

        # check that patient names are correctly written back
        # without original byte string (PersonName3 only)
        if hasattr(ds.PatientName, 'original_string'):
            ds.PatientName.original_string = None
            fp = DicomBytesIO()
            fp.is_implicit_VR = False
            fp.is_little_endian = True
            ds.save_as(fp, write_like_original=False)
            fp.seek(0)
            ds = dcmread(fp)
            assert patient_name == ds.PatientName

    def test_changed_character_set(self):
        # Regression test for #629
        multiPN_name = get_charset_files("chrFrenMulti.dcm")[0]
        ds = dcmread(multiPN_name)  # is Latin-1
        ds.SpecificCharacterSet = 'ISO_IR 192'
        from pydicom.filebase import DicomBytesIO
        fp = DicomBytesIO()
        ds.save_as(fp, write_like_original=False)
        fp.seek(0)
        ds_out = dcmread(fp)
        # we expect UTF-8 encoding here
        assert b'Buc^J\xc3\xa9r\xc3\xb4me' == ds_out.get_item(0x00100010).value

    def test_invalid_second_encoding(self):
        # regression test for #850
        elem = DataElement(0x00100010, 'PN', 'CITIZEN')
        with pytest.warns(UserWarning,
                          match=u"Unknown encoding 'ISO 2022 IR 146' "
                                u"- using default encoding instead"):
            pydicom.charset.decode_element(
                elem, ['ISO 2022 IR 100', 'ISO 2022 IR 146'])

    def test_japanese_multi_byte_personname(self):
        """Test japanese person name which has multi byte strings are
        correctly encoded."""
        file_path = get_charset_files('chrH32.dcm')[0]
        ds = dcmread(file_path)
        ds.decode()

        if hasattr(ds.PatientName, 'original_string'):
            original_string = ds.PatientName.original_string
            ds.PatientName.original_string = None
            fp = DicomBytesIO()
            fp.is_implicit_VR = False
            fp.is_little_endian = True
            ds.save_as(fp, write_like_original=False)
            fp.seek(0)
            ds_out = dcmread(fp)
            assert original_string == ds_out.PatientName.original_string

    def test_japanese_multi_byte_encoding(self):
        """Test japanese multi byte strings are correctly encoded."""
        encoded = pydicom.charset.encode_string(u'あaｱア',
                                                ['shift_jis', 'iso2022_jp'])
        assert b'\x1b$B$"\x1b(Ja\x1b)I\xb1\x1b$B%"\x1b(J' == encoded

    def test_bad_japanese_encoding(self):
        """Test japanese multi byte strings are not correctly encoded."""
        with pytest.warns(UserWarning,
                          match=u"Failed to encode value with encodings"
                                u": shift_jis - using replacement character"
                                u"s in encoded string"):
            encoded = pydicom.charset.encode_string(u'あaｱア', ['shift_jis'])
            assert b'?a??' == encoded

    def test_deprecated_decode(self):
        """Test we get a deprecation warning when using charset.decode()."""
        # Python 3: elem.value is PersonName3, Python 2: elem.value is str
        elem = DataElement(0x00100010, 'PN', 'CITIZEN')
        msg = r"'charset.decode\(\)' is deprecated"
        with pytest.warns(DeprecationWarning, match=msg):
            pydicom.charset.decode(elem, ['ISO 2022 IR 126'])
