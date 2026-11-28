"""AC-12: la migración 0002 conserva las conversaciones existentes sin vínculos y es reversible."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [('messaging', '0001_initial')]
AFTER = [('messaging', '0002_conversation_inbox_links')]
COMPANY = '00000000-0000-4000-8000-0000000000aa'


class InboxLinksMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        MigrationExecutor(connection).migrate(targets)
        return MigrationExecutor(connection).loader.project_state(targets).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_existing_conversations_keep_their_data_without_links_and_it_reverses(self):
        old = self.migrate(BEFORE)
        link = old.get_model('messaging', 'ConnectionModel').objects.create(
            company_id=COMPANY, waba_id='9', phone_number_id='555', secret_ref='WHATSAPP_X_T',
            app_secret_ref='WHATSAPP_X_A', verify_token='v-mig')
        old.get_model('messaging', 'ConversationModel').objects.create(
            company_id=COMPANY, connection=link, phone='59176543210')

        new = self.migrate(AFTER)
        row = new.get_model('messaging', 'ConversationModel').objects.get(phone='59176543210')
        self.assertEqual((row.owner_id, row.customer_id, row.lead_id, row.opportunity_id), (None,) * 4)

        back = self.migrate(BEFORE)
        kept = back.get_model('messaging', 'ConversationModel').objects.filter(phone='59176543210')
        self.assertEqual(kept.count(), 1)
