from odoo import _, api, fields, models

class ChangeRole(models.TransientModel):
    _name = 'change.role'
    _description = 'Change Role'

    user_ids = fields.Many2many(
        'res.users', 
        'change_id', 
        'user_id', 
        'change_role_users_rel', 
        string='Users', 
        required=True
    )
    user_role_id = fields.Many2one('res.users.role', string='Role', required=True)

    def change_role(self):
        for user in self.user_ids:
            user.role_line_ids = [(6,0,[])]
            role = self.user_role_id
            group_ids = set(
                    role.group_id.ids
                    + role.implied_ids.ids
                    + role.trans_implied_ids.ids
                )
            groups_to_add = list(set(group_ids) - set(user.groups_id.ids))
            groups_to_remove = list(set(user.groups_id.ids) - set(group_ids))
            to_add = [(4, gr) for gr in groups_to_add]
            to_remove = [(3, gr) for gr in groups_to_remove]
            groups = to_remove + to_add
            if groups:
                vals = {"groups_id": groups, "role_line_ids": [(0,0,{'role_id': role.id, 'is_enabled': True})]}
                user.write(vals)
        return True