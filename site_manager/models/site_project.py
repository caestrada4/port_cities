from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProjectProject(models.Model):
    _inherit = "project.project"

    deadline = fields.Date(string="Deadline")
    budget = fields.Monetary(string="Budget")
    currency_id = fields.Many2one('res.currency', string='Currency')
    project_size = fields.Selection([('small','Small'),('medium','Medium'),('large','Large')], string="Project Size")
    stage_id = fields.Many2one('project.task.type', string='Stage')

    # override write to validate requirements when stage changes
    def write(self, vals):
        # detect stage change
        if 'stage_id' in vals:
            new_stage = vals.get('stage_id')
            # perform validation for each record
            for rec in self:
                # call helper that raises ValidationError if not met
                rec._validate_stage_requirements(new_stage)
        return super().write(vals)

    def _validate_stage_requirements(self, stage_id):
        """Checks dynamic requirements configured for this model and stage.
        If missing, raises ValidationError with list of missing fields."""
        if not stage_id:
            return True
        Requirement = self.env['site.dynamic.requirement']
        # search requirements for this stage for model project.project
        reqs = Requirement.search([('model_name','=','project.project'),('stage_id','=',int(stage_id))])
        missing = []
        for r in reqs:
            field_name = r.field_name
            # Skip if field doesn't exist
            if field_name not in self._fields:
                continue
            val = getattr(self, field_name, False)
            # consider zero/False as missing except numeric? use simple rule: falsy -> missing
            if not val:
                missing.append(field_name)
        if missing:
            raise ValidationError(_("Can't move to the selected stage. Missing required fields: %s") % ', '.join(missing))
        return True
