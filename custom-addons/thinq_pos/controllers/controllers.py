from odoo import http
from odoo.http import request

class ThinqPosReportController(http.Controller):
    @http.route('/thinq_pos/report/pos_order/invoice/<int:order_id>', type='http', auth='public', website=True)
    def thinq_pos_report_pos_invoice(self, order_id):
        order_id = request.env['pos.order'].sudo().browse(order_id)
        if not order_id:
            return 'POS Order Not Found'
        pdf, _ = request.env['ir.actions.report']._render_qweb_pdf('thinq_pos.action_report_pos_invoice', [order_id.id])
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename="%s.pdf"' % (order_id.name)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
