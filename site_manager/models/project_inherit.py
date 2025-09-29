# -*- coding: utf-8 -*-
from odoo import models, fields


class ProjectProject(models.Model):
    _inherit = "project.project"

    # new fields
    deadline_date = fields.Datetime(string="Deadline Date")
    budget = fields.Float(string="Budget")
    project_size = fields.Selection([
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
    ], string="Project Size")
    stage_site_id = fields.Many2one('project.task', string="Milestone")
