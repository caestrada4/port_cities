# addons/site_manager/models/dynamic_requirement.py
from odoo import models, fields, api

class SiteDynamicRequirement(models.Model):
    _name = "site.dynamic.requirement"
    _description = "Dynamic requirement mapping by stage"

    name = fields.Char(string="Description", required=True)
    model_name = fields.Char(string="Model Name", required=True, default='project.project')
    field_name = fields.Char(string="Field Name", required=True,
                             help="Field python name on the model (e.g. budget, deadline)")
    stage_id = fields.Many2one('project.task.type', string="Stage", required=True)
    # you can add more metadata: error_message, sequence, active
    error_message = fields.Char(string="Custom message")
