from odoo import _, api, fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    is_custom_role = fields.Boolean(compute='_custom_role', store=True)

    @api.depends('role_ids','groups_id')
    def _custom_role(self):
        for rec in self:
            role_groups = {}
            for role in self.mapped("role_line_ids.role_id"):
                role_groups[role] = list(
                    set(
                        role.group_id.ids
                        + role.implied_ids.ids
                        + role.trans_implied_ids.ids
                    )
                )
            group_ids = []
            for role_line in rec._get_enabled_roles():
                role = role_line.role_id
                group_ids += role_groups[role]
            group_ids = list(set(group_ids))
            if rec.groups_id.ids and group_ids:
                if set(rec.groups_id.ids) != set(group_ids):
                    rec.is_custom_role = True
                else:
                    rec.is_custom_role = False
            else:
                rec.is_custom_role = False

    def action_change_role_bulk(self):
        action = self.env.ref('thinq_base.change_role_action').read()[0]
        action['context'] = {'default_user_ids': self.ids}
        return action