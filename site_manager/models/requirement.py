# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class DynamicRequirementField(models.Model):
    _name = "dynamic.requirement.field"
    _description = "Dynamic Requirement (Group)"

    name = fields.Char(string="Name", required=True, default="New")
    sequence = fields.Integer(string="Sequence", default=10)
    type = fields.Selection([('site', 'Site'), ('milestone', 'Milestone')], string="Type", required=True, default='site')
    active = fields.Boolean(string="Active", default=True)
    line_ids = fields.One2many('dynamic.requirement.field.line', 'requirement_id', string="Requirement Lines")
    company_id = fields.Many2one('res.company', string='Company')


class DynamicRequirementFieldLine(models.Model):
    _name = "dynamic.requirement.field.line"
    _description = "Dynamic Requirement Field Line"
    _order = "sequence, id"

    sequence = fields.Integer(string="Sequence", default=10)
    requirement_id = fields.Many2one('dynamic.requirement.field', string="Requirement", ondelete='cascade', required=True)
    stage_id = fields.Many2one('project.task', string="Milestone", required=True)
    mandatory_fields = fields.Many2many('ir.model.fields', 'req_line_model_fields_rel', 'line_id', 'field_id', string="Mandatory Fields")
    custom_warning_msg = fields.Char(string="Custom Warning Message")
    company_id = fields.Many2one('res.company', string='Company')

    # domain or constraints could be added to ensure model is project.project fields

class ProjectProject(models.Model):
    _inherit = "project.project"

    requirement_id = fields.Many2one('dynamic.requirement.field', string="Requirement")

    @api.model
    def _check_record_mandatory_for_stage(self, project_rec, dest_stage):
        """Return (ok True/False, message) for a single project record and dest_stage (record)."""
        if not project_rec.requirement_id:
            return True, ''
        # Find the matching line for dest_stage (same company or no company)
        lines = project_rec.requirement_id.line_ids.filtered(
            lambda l: l.stage_id and l.stage_id.id == dest_stage.id and (not l.company_id or l.company_id == project_rec.company_id)
        )
        if not lines:
            return True, ''
        # take first matching line (you can extend for multiples)
        line = lines[0]
        missing = []
        for irf in line.mandatory_fields:
            # make sure the field belongs to project.project model
            if irf.model != 'project.project':
                # skip fields not on this model
                continue
            fname = irf.name
            # safe getattr (if relation fields, will return recordset)
            try:
                val = project_rec[fname]
            except Exception:
                val = False
            # evaluate emptiness depending on field type:
            if val is False or val is None or val == '':
                missing.append(irf.field_description or fname)
            else:
                # if recordset (many2one/many2many), check emptiness
                if hasattr(val, '__len__') and len(val) == 0:
                    missing.append(irf.field_description or fname)
        if missing:
            if line.custom_warning_msg:
                return False, line.custom_warning_msg
            else:
                return False, _('Missing required fields: %s') % (', '.join(missing))
        return True, ''

    def write(self, vals):

        if 'stage_id' in vals:
            # If stage is set to falsy, skip
            new_stage_id = vals.get('stage_id')
            for rec in self:
                # determine destination stage record
                dest_stage = False
                if isinstance(new_stage_id, (list, tuple)):

                    if new_stage_id and isinstance(new_stage_id[0], int):
                        # take second element if (4, id)
                        if len(new_stage_id) >= 2 and isinstance(new_stage_id[1], int):
                            dest_stage = self.env['project.task'].browse(new_stage_id[1])
                elif isinstance(new_stage_id, int):
                    dest_stage = self.env['project.task'].browse(new_stage_id)
                elif isinstance(new_stage_id, bool) and not new_stage_id:
                    dest_stage = False
                else:
                    try:
                        sid = int(new_stage_id)
                        dest_stage = self.env['project.task'].browse(sid)
                    except Exception:
                        dest_stage = False

                if dest_stage and dest_stage.exists():
                    ok, msg = self._check_record_mandatory_for_stage(rec, dest_stage)
                    if not ok:
                        raise ValidationError(msg)
        return super(ProjectProject, self).write(vals)
