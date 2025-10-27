import base64
from collections import OrderedDict
from datetime import datetime

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request, Response
from odoo.tools import image_process
from odoo.tools.translate import _
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager
import json


class CustomerPortal(portal.CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        # PurchaseRequest = request.env['purchase.request']
        if 'pr_count' in counters:
        #     values['pr_count'] = PurchaseRequest.search_count([('requested_by','=',request.env.user.id)]) if PurchaseRequest.has_access('read') else 0
            values['pr_count'] = 1
        return values
    
    def _get_pr_searchbar_sortings(self):
        return {
            'date': {'label': _('Newest'), 'order': 'date_start desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'estimated_cost desc, id desc'},
        }
    
    def _render_pr_portal(self, template, page, date_begin, date_end, sortby, filterby, domain, searchbar_filters, default_filter, url, history, page_name, key):
        values = self._prepare_portal_layout_values()
        PurchaseRequest = request.env['purchase.request']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = self._get_pr_searchbar_sortings()
        # default sort
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if searchbar_filters:
            # default filter
            if not filterby:
                filterby = default_filter
            domain += searchbar_filters[filterby]['domain']

        # count for pager
        count = PurchaseRequest.search_count(domain)

        # make pager
        pager = portal_pager(
            url=url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=count,
            page=page,
            step=self._items_per_page
        )

        # search the purchase orders to display, according to the pager data
        orders = PurchaseRequest.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session[history] = orders.ids[:100]

        values.update({
            'date': date_begin,
            key: orders,
            'page_name': page_name,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': url,
        })
        return request.render(template, values)
    
    @http.route(['/my/pr', '/my/pr/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_prs(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        return self._render_pr_portal(
            "thinq_purchase.portal_my_prs",
            page, date_begin, date_end, sortby, filterby,
            [('requested_by','=',request.env.user.id)],
            {},
            None,
            "/my/pr",
            'my_prs_history',
            'pr',
            'prs'
        )
    
    @http.route(['/my/pr/<int:request_id>'], type='http', auth="public", website=True)
    def portal_my_purchase_request(self, request_id=None, access_token=None, **kw):
        try:
            request_sudo = self._document_check_access('purchase.request', request_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        report_type = kw.get('report_type')
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(
                model=request_sudo,
                report_type=report_type,
                report_ref='purchase_request.action_report_purchase_requests',
                download=kw.get('download')
            )

        values = self._purchase_request_get_page_view_values(request_sudo, access_token, **kw)
        if request_sudo.company_id:
            values['res_company'] = request_sudo.company_id

        return request.render("thinq_purchase.portal_my_purchase_request", values)


    def _purchase_request_get_page_view_values(self, request_obj, access_token, **kwargs):

        def resize_to_48(source):
            if not source:
                source = request.env['ir.binary']._placeholder()
            else:
                source = base64.b64decode(source)
            return base64.b64encode(image_process(source, size=(48, 48)))

        values = {
            'pr': request_obj,
            'resize_to_48': resize_to_48,
            'report_type': 'html',
        }

        history = 'my_prs_history'
        return self._get_page_view_values(request_obj, access_token, values, history, False, **kwargs)

    
    @http.route('/product/search', type='http', auth='user', csrf=False)
    def portal_product_search(self, **kw):
        q = kw.get('q', '')
        domain = [('purchase_ok','=',True)]
        if q:
            domain += ['|', ('name', 'ilike', q), ('default_code', 'ilike', q)]
        products = request.env['product.product'].sudo().search_read(
            domain=domain,
            order='name asc, id asc',
            limit=40
        )
        result = [{'id': p['id'], 'name': p['display_name']} for p in products]
        return request.make_response(
            json.dumps(result),
            headers=[('Content-Type', 'application/json')]
        )
    
    @http.route(['/my/pr/create'], type='http', auth='user', website=True)
    def portal_create_pr(self):
        company_ids = request.env['res.company'].sudo().search_read(
            domain=[],
            fields=['id','name'],
            order='id asc, parent_id asc'
        )

        approver_group = request.env.ref('purchase_request.group_purchase_request_manager')
        approver_ids = request.env['res.users'].sudo().search_read(
            domain=[('groups_id', 'in', [approver_group.id])],
            fields=['id', 'display_name'],
            order='name asc',
        )

        values = {
            'error': {},
            'error_message': [],
            'page_name': 'create_pr',
            'current_user': request.env.user,
            'companies': company_ids,
            'approvers': approver_ids
        }

        return request.render("thinq_purchase.portal_create_pr", values)

    @http.route(['/my/pr/submit'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_submit_pr(self, **post):
        user = request.env.user
        expected_date = post.get('expected_date')
        vals = {
            'requested_by': user.id,
            'assigned_to': int(post.get('assigned_to')),
            'date_planned': datetime.strptime(expected_date, '%m/%d/%Y').strftime('%Y-%m-%d') if expected_date else False,
            'company_id': int(post.get('company_id')),
            'origin': post.get('origin'),
            'description': post.get('description'),
        }
        pr = request.env['purchase.request'].sudo().create(vals)

        # handle lines
        product_ids = request.httprequest.form.getlist('product_id[]')
        qtys = request.httprequest.form.getlist('product_qty[]')
        prices = request.httprequest.form.getlist('price_unit[]')

        for pid, qty, price in zip(product_ids, qtys, prices):
            if pid:
                pr_line = request.env['purchase.request.line'].sudo().create({
                    'request_id': pr.id,
                    'product_id': int(pid),
                    'name': request.env['product.product'].sudo().search_read(domain=[('id','=',int(pid))],fields=['display_name'])[0]['display_name'],
                    'product_qty': float(qty or 0),
                    'price_unit': float(price or 0),
                })
                pr_line.sudo()._compute_supplier_id()
        
        pr.button_to_approve()

        return request.redirect('/my/pr')