from odoo import models, fields, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    approve_by_manager = fields.Boolean(
        string="Manager Approval for Inter-Warehouse",
        config_parameter='warehouse_inter_transfer_app.approve_by_manager'
    )


class ResCompany(models.Model):
    _inherit = "res.company"

    approve_by_manager = fields.Boolean("Approve By Manager")
