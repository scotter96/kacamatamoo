from odoo import http
from odoo.http import request

class UrlShortenerController(http.Controller):

    @http.route('/s/<string:code>', type='http', auth='public', website=True)
    def redirect_short_url(self, code, **kwargs):
        short = request.env['url.shortener'].sudo().search([('name', '=', code)], limit=1)
        if short:
            short.sudo().write({'click_count': short.click_count + 1})
            return request.redirect(short.original_url)
        return request.not_found()