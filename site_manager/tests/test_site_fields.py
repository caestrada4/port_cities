# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestSiteFields(TransactionCase):

    def test_project_new_fields_exist(self):
        """Comprobar que los campos añadidos al modelo project.project existen y tienen el label esperado."""
        Project = self.env['project.project']
        expected_fields = ['deadline_date', 'budget', 'project_size', 'stage_site_id', 'requirement_id']
        for fname in expected_fields:
            self.assertIn(fname, Project._fields, msg="Falta el campo %s en project.project" % fname)

        if 'deadline_date' in Project._fields:
            self.assertEqual(Project._fields['deadline_date'].string, 'Deadline Date')
        if 'budget' in Project._fields:
            self.assertEqual(Project._fields['budget'].string, 'Budget')
        if 'project_size' in Project._fields:
            self.assertIn(Project._fields['project_size'].string, ['Project Size', 'Project size', 'Project Size'])
