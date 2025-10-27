from odoo import fields, models, api

class ContactResult(models.Model):
    _name = 'thinq.project.contact.result'
    _description = 'Contact Result'

    name = fields.Char(required=True)

class VisitStatus(models.Model):
    _name = 'thinq.project.visit.status'
    _description = 'Visit Status'

    name = fields.Char(required=True)