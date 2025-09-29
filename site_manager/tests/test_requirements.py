# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestDynamicRequirements(TransactionCase):

    def setUp(self):
        super(TestDynamicRequirements, self).setUp()
        self.Stage = self.env['site.stage']
        self.Req = self.env['dynamic.requirement.field']
        self.ReqLine = self.env['dynamic.requirement.field.line']
        self.Project = self.env['project.project']
        self.IrField = self.env['ir.model.fields']
        self.Partner = self.env['res.partner']

        self.stage_from = self.Stage.create({'name': 'Stage A'})
        self.stage_to = self.Stage.create({'name': 'Stage B'})

        self.partner_field = self.IrField.search([('model','=','project.project'), ('name','=','partner_id')], limit=1)
        if not self.partner_field:
            self.partner_field = self.IrField.search([('model','=','project.project')], limit=1)
        if not self.partner_field:
            raise AssertionError("No se encontró ningún campo en ir.model.fields para project.project")

    def test_move_stage_missing_mandatory_raises(self):
        """Si la línea exige partner_id y el project no lo tiene, al mover a la stage destino debe fallar"""
        req = self.Req.create({'name': 'Req Missing Partner', 'type': 'site'})
        line_vals = {
            'requirement_id': req.id,
            'stage_id': self.stage_to.id,
            'mandatory_fields': [(6, 0, [self.partner_field.id])],
            'custom_warning_msg': 'Customer is mandatory for this stage'
        }
        self.ReqLine.create(line_vals)

        proj = self.Project.create({'name': 'Site no Partner', 'company_id': self.env.company.id})
        proj.requirement_id = req

        with self.assertRaises(ValidationError) as cm:
            proj.write({'stage_id': self.stage_to.id})
        msg = str(cm.exception) or ''
        self.assertTrue('customer' in msg.lower() or 'mandatory' in msg.lower() or 'oblig' in msg.lower())

    def test_move_stage_with_mandatory_ok(self):
        """Si el campo obligatorio está relleno, el cambio de stage debe permitirse"""
        req = self.Req.create({'name': 'Req OK', 'type': 'site'})
        self.ReqLine.create({
            'requirement_id': req.id,
            'stage_id': self.stage_to.id,
            'mandatory_fields': [(6, 0, [self.partner_field.id])],
        })

        proj = self.Project.create({'name': 'Site OK', 'company_id': self.env.company.id})
        proj.requirement_id = req

        partner = self.Partner.create({'name': 'ACME Test'})
        proj.partner_id = partner

        proj.write({'stage_id': self.stage_to.id})
        self.assertEqual(proj.stage_id.id, self.stage_to.id)

    def test_custom_warning_message_is_shown(self):
        """Si hay custom_warning_msg configurada, la ValidationError debe contener exactamente ese texto (o al menos incluirlo)."""
        custom_msg = "Fields Customer and Deadline are mandatory"
        req = self.Req.create({'name': 'Req Custom Msg', 'type': 'site'})
        self.ReqLine.create({
            'requirement_id': req.id,
            'stage_id': self.stage_to.id,
            'mandatory_fields': [(6, 0, [self.partner_field.id])],
            'custom_warning_msg': custom_msg,
        })

        proj = self.Project.create({'name': 'Site Custom Msg', 'company_id': self.env.company.id})
        proj.requirement_id = req

        with self.assertRaises(ValidationError) as cm:
            proj.write({'stage_id': self.stage_to.id})
        self.assertIn(custom_msg, str(cm.exception))
