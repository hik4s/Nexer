import io
import json
import unittest
from unittest.mock import Mock, patch
from app.services.target_pickings import TargetPickings


class TargetPickingsTests(unittest.TestCase):
    def manager(self, messages, *, clock=lambda: 0):
        process = Mock(stdin=io.StringIO(), stdout=io.StringIO(''.join(json.dumps(m)+'\n' for m in messages)))
        process.poll.return_value = 0
        manager = TargetPickings(session_valid=lambda owner: owner == 'owner', start_process=lambda: process, clock=clock)
        return manager, process

    def test_done_protocol_validates_metadata_and_owner(self):
        manager, process = self.manager([{'type':'phase','phase':'SELECTING'}, {'type':'done','target':{'selector':'#search'}}])
        result = manager.start_target('owner','https://example.test/form','text')
        manager._entries[result['id']]['thread'].join(timeout=2)
        result = manager.get(result['id'],'owner')
        self.assertEqual(result['target'], {'selector':'#search'})
        self.assertEqual(result['status'],'DONE')
        self.assertNotIn('owner',result)
        with self.assertRaises(RuntimeError): manager.get(result['id'],'other')

    def test_unexpected_data_errors_and_done_before_selection_fail_closed(self):
        cases=[[],[{'type':'done','target':{'selector':'#search'}}],
               [{'type':'phase','phase':'SELECTING'},{'type':'done','target':{'selector':'input[value="private-canary"]'}}],
               [{'type':'error','code':'private-canary'}]]
        for messages in cases:
            manager,_=self.manager(messages)
            result=manager.start_target('owner','https://example.test/','element')
            manager._entries[result['id']]['thread'].join(timeout=2)
            result=manager.get(result['id'],'owner')
            self.assertEqual(result['status'],'FAILED')
            self.assertIsNone(result['target'])
            self.assertNotIn('private-canary',json.dumps(result))

    def test_cancel_and_expiry_prevent_late_target_delivery(self):
        now=[0]
        manager, process=self.manager([],clock=lambda:now[0])
        entry=manager._new_entry('owner',0,1);entry['process']=process
        manager._entries[entry['id']]=entry
        self.assertEqual(manager.cancel(entry['id'],'owner')['status'],'CANCELLED')
        process.stdout=io.StringIO(json.dumps({'type':'done','target':{'selector':'#search'}})+'\n')
        manager._read(entry)
        self.assertIsNone(manager.get(entry['id'],'owner')['target'])
        now[0]=301
        with self.assertRaises(RuntimeError): manager.get(entry['id'],'owner')

    def test_invalid_configuration_never_launches(self):
        manager, process=self.manager([])
        with self.assertRaises(ValueError): manager.start_target('owner','http://other.test/','text')
        self.assertEqual(manager._entries,{})

    def test_capacity_and_session_revocation_are_enforced(self):
        valid=[True]
        manager=TargetPickings(session_valid=lambda owner:valid[0],start_process=Mock())
        for _ in range(2):
            entry=manager._new_entry('owner',0,1);manager._entries[entry['id']]=entry
        with self.assertRaisesRegex(RuntimeError,'CAPACITY'):
            manager.start_target('owner','https://example.test/','element')
        manager._start_process.assert_not_called()
        valid[0]=False;manager.sweep()
        self.assertEqual(manager._entries,{})

    def test_api_uses_authenticated_owner_no_store_and_strict_input(self):
        from test_client import AuthenticatedTestClient
        from app.main import app
        fake=Mock()
        fake.start_target.return_value={'id':'session','status':'RECORDING','phase':'PREPARING','target':None,'error':None}
        with patch('app.api.target_pickings.target_pickings',fake):
            client=AuthenticatedTestClient(app)
            response=client.post('/target-pickings',json={'url':'https://example.test/','kind':'text'})
            self.assertEqual(response.status_code,201)
            self.assertEqual(response.headers['Cache-Control'],'no-store')
            self.assertIsInstance(fake.start_target.call_args.args[0],str)
            self.assertEqual(client.post('/target-pickings',json={'url':'https://example.test/','kind':'text','value':'private'}).status_code,422)
            client.cookies.clear()
            self.assertEqual(client.get('/target-pickings/session').status_code,401)
