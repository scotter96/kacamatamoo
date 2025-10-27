from odoo import api, fields, models


class LoyaltyRewardInherit(models.Model):
    _inherit = 'loyalty.reward'

    has_birthday_reward = fields.Boolean('Has Birthday Rewards', compute='_compute_reward')


    def _compute_reward(self):
        for record in self:
            record.has_birthday_reward = self.has_birthday_rule(record.program_id)

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        if 'has_birthday_reward' not in fields:
            fields.append('has_birthday_reward')
        return fields

    def has_birthday_rule(self, program_id):
        return program_id.check_partner_birthday
