"""Regression tests for Weekly Inventory Report recipient management."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch


project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestEmailDistributionList(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as dashboard_app

        cls.dashboard_app = dashboard_app

    def test_email_normalization_is_case_insensitive_and_validated(self):
        normalize = self.dashboard_app._normalize_email_contact_address

        self.assertEqual(normalize('  Person@Example.COM  '), 'person@example.com')
        self.assertIsNone(normalize('not-an-email'))
        self.assertIsNone(normalize('person@example'))
        self.assertIsNone(normalize(''))

    def test_create_rejects_case_insensitive_duplicate(self):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (13,)
        conn.cursor.return_value = cursor

        with patch('app.get_connection', return_value=conn):
            with self.dashboard_app.app.test_request_context(
                '/api/email_contacts',
                method='POST',
                json={'email': ' QUINN@EXAMPLE.COM ', 'name': 'Quinn'},
            ):
                response, status = self.dashboard_app.api_create_email_contact()

        self.assertEqual(status, 400)
        self.assertEqual(
            response.get_json()['error'],
            'This email is already on the distribution list',
        )
        cursor.execute.assert_called_once_with(
            'SELECT 1 FROM email_contacts WHERE LOWER(email) = %s',
            ('quinn@example.com',),
        )
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    def test_create_stores_normalized_address(self):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.side_effect = [None, (42,)]
        conn.cursor.return_value = cursor

        with patch('app.get_connection', return_value=conn):
            with self.dashboard_app.app.test_request_context(
                '/api/email_contacts',
                method='POST',
                json={'email': ' Recipient@Example.COM ', 'name': 'Recipient'},
            ):
                response = self.dashboard_app.api_create_email_contact()

        self.assertEqual(response.status_code, 200)
        insert_call = cursor.execute.call_args_list[1]
        self.assertEqual(insert_call.args[1], ('recipient@example.com', 'Recipient'))
        conn.commit.assert_called_once()

    def test_compose_flows_review_recipients_before_mailto(self):
        with open(os.path.join(project_root, 'index.html'), encoding='utf-8') as page:
            dashboard = page.read()
        with open(
            os.path.join(project_root, 'email_contacts.html'),
            encoding='utf-8',
        ) as page:
            contacts_page = page.read()

        dashboard_compose = dashboard[
            dashboard.index('async function copyWeeklyInventoryToClipboard'):
            dashboard.index('// Helper function to format relative time')
        ]
        contacts_compose = contacts_page[
            contacts_page.index('async function composeEmailToAll'):
        ]

        self.assertIn('Manage Recipients', dashboard)
        self.assertIn('Weekly Report Distribution List', contacts_page)
        self.assertIn('recipientReview', dashboard_compose)
        self.assertIn('recipientReview', contacts_compose)
        self.assertLess(
            dashboard_compose.index('const confirmed = confirm('),
            dashboard_compose.index('const mailtoLink ='),
        )
        self.assertLess(
            contacts_compose.index('const confirmed = confirm('),
            contacts_compose.index('const mailtoLink ='),
        )


if __name__ == '__main__':
    unittest.main()