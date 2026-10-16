import unittest
from field_schema import validate_field
from recipe import validate_recipe, RecipeValidationError


class CalendarMetadataContractTests(unittest.TestCase):
    def test_static_datetime_mask_can_be_published_without_a_value(self):
        field={'control':'datetime-local','site_format':'dd/MM/yyyy HH:mm:ss','required':False}
        self.assertEqual(validate_field(field),field)
        recipe={'schema_version':1,'name':'Date mask','variables':{
            'input_001':{'type':'string','required':True,'label':'Data Hora Início','field':field}
        },'steps':[{'id':'search','action':'fill','selector':'#start','value':'{{input_001}}'}],
         'output':{'type':'none'}}
        self.assertEqual(validate_recipe(recipe)['variables']['input_001']['field'],field)

    def test_mask_does_not_accept_arbitrary_text_or_mismatched_controls(self):
        for field in [
            {'control':'text','site_format':'dd/MM/yyyy HH:mm:ss'},
            {'control':'datetime-local','site_format':'dd/MM/yyyy'},
            {'control':'date','site_format':'dd/MM/yyyy HH:mm:ss'},
            {'control':'datetime-local','site_format':'value=private-canary'}
        ]:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError,'FIELD_SCHEMA_INVALID'):
                    validate_field(field)
