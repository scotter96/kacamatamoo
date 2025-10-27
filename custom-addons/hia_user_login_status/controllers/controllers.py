# -*- coding: utf-8 -*-
from odoo import http, SUPERUSER_ID
from odoo.addons.web.controllers.home import Home as WebHome
from odoo.addons.web.controllers.session import Session
from odoo.http import request
from datetime import datetime
import logging


_logger = logging.getLogger(__name__)




class UserLogin(WebHome):

    @http.route()
    def web_login(self, redirect=None, **kw):
        res = super(UserLogin, self).web_login(redirect=redirect, **kw)
        if request.params.get('login_success'):
            user = request.env['res.users'].sudo().search([('login', '=', kw.get('login'))], limit=1)
            if user and user.exists():
                try:
                    user.sudo().write({'status': 'done'})
                    config_params = request.env['ir.config_parameter'].sudo()
                    if config_params.get_param('hia_user_login_status.store_user_time'):
                        request.env['res.users.logger'].sudo().create({
                            'username': user.id,
                            'login_time': datetime.now()
                        })
                except Exception as e:
                    request.env.cr.rollback()
                    _logger.warning("Failed to update login status for user %s: %s", user.login, e)
        return res


class UserSession(Session):
    @http.route()
    def logout(self, redirect='/odoo'):
        uid = request.session.uid
        user = request.env['res.users'].sudo().browse(uid)
        if user.exists():
            _logger.info(f"User {user.login} is logging out.")
            user.with_user(SUPERUSER_ID).write({'status': 'blocked'})
            config_perams = request.env['ir.config_parameter'].sudo()
            need_to_store = config_perams.get_param('hia_user_login_status.store_user_time')
            if need_to_store:
                record = request.env['res.users.logger'].sudo().search(
                    [('username', '=', user.id), ('logout_time', '=', False)], limit=1)
                if record:
                    record.logout_time = datetime.now()
        return super(UserSession, self).logout(redirect=redirect)
