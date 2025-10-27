from odoo import api, fields, models, _
from odoo.exceptions import UserError
import re

class MultipleSearch(models.TransientModel):
    _name = 'multiple.search'
    _description = 'Multiple Search Wizard'

    keyword = fields.Char(
        string='Search Keyword', 
        required=True,
        help='Enter keyword(s) to search. Use comma, space, or new line to separate multiple keywords'
    )
    
    search_model = fields.Selection([
        ('account.move', 'Invoices/Journal Entries'),
        ('account.move.line', 'Journal Items'),
        ('pos.order', 'Point of Sale'),  # Ubah label untuk lebih komprehensif
        ('account.payment', 'Vendor Bills'),
        ('sale.order', 'Sales Orders'),
        ('purchase.order', 'Purchase Orders'),
        ('purchase.request', 'Purchase Requests'),
        ('all', 'All Documents'),
    ], string='Search In', default='all', required=True)

    @api.model
    def default_get(self, fields_list):
        """Override default_get to handle context properly"""
        res = super().default_get(fields_list)
        
        # Get search model from context
        context_model = self.env.context.get('search_model')
        if context_model and 'search_model' in fields_list:
            res['search_model'] = context_model
            
        return res

    def _parse_keywords(self, keyword_string):
        """Parse multiple keywords from input string"""
        # Split by comma, semicolon, new line, or multiple spaces
        keywords = re.split(r'[,;\n\r]+|\s{2,}', keyword_string.strip())
        # Clean up and filter empty strings
        keywords = [kw.strip() for kw in keywords if kw.strip()]
        return keywords

    def action_search(self):
        """Execute search based on keyword and selected model"""
        if not self.keyword:
            raise UserError(_("Please enter a keyword to search"))

        # Parse multiple keywords
        keywords = self._parse_keywords(self.keyword)
        
        # Get search model from context if provided (for specific menu calls)
        context_model = self.env.context.get('search_model')
        if context_model:
            search_model = context_model
        else:
            search_model = self.search_model

        if search_model == 'all':
            return self._search_all_models(keywords)
        else:
            return self._search_specific_model(keywords, search_model)

    def _search_specific_model(self, keywords, model_name):
        """Search in a specific model with multiple keywords"""
        # Define search fields for each model
        model_fields = {
            'account.move': ['name', 'ref', 'partner_id.name', 'invoice_origin', 'narration'],
            'account.move.line': ['name', 'ref', 'partner_id.name', 'move_id.name', 'account_id.name'],
            'pos.order': [ 'name', 'pos_reference', 'partner_id.name', 'user_id.name', 'session.name', 'config_id.name', 'note'],
            'sale.order': ['name', 'client_order_ref', 'partner_id.name', 'origin', 'user_id.name'],
            'purchase.order': ['name', 'partner_ref', 'partner_id.name', 'origin', 'user_id.name', 'company_id.name', 'notes'],
            'purchase.request': ['name', 'description', 'requested_by.name', 'company_id.name', 'origin','line_ids.product_id.name','picking_type_id.name'],
        }

        # Special handling for comprehensive POS search
        search_type = self.env.context.get('search_type', 'document')
        if search_type == 'pos_comprehensive' and model_name == 'pos.order':
            return self._search_pos_comprehensive(keywords)

        if model_name not in model_fields:
            raise UserError(_("Search not supported for model: %s") % model_name)

        # Build search using simple OR approach - collect all record IDs
        search_fields = model_fields[model_name]
        all_record_ids = set()
        
        # Search for each keyword separately and combine results
        for keyword in keywords:
            for field in search_fields:
                try:
                    # Create simple domain for this keyword and field
                    domain = [(field, 'ilike', keyword)]
                    
                    # Add extra domain based on search type
                    if model_name == 'account.move':
                        search_type = self.env.context.get('search_type', 'invoice')
                        if search_type == 'bill':
                            domain.append(('move_type', 'in', ['in_invoice', 'in_refund']))
                        elif search_type == 'journal_entry':
                            domain.append(('move_type', '=', 'entry'))
                        else:
                            domain.append(('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']))
                    
                    # Search and collect IDs
                    records = self.env[model_name].search(domain)
                    all_record_ids.update(records.ids)
                except Exception as e:
                    # Skip if search fails for this field
                    continue

        # Convert to list
        record_ids = list(all_record_ids)

        if not record_ids:
            search_type = self.env.context.get('search_type', 'document')
            if search_type == 'bill':
                document_type = 'bills'
            elif search_type == 'invoice':
                document_type = 'invoices'
            elif search_type == 'journal_entry':
                document_type = 'journal entries'
            elif search_type == 'journal_items':
                document_type = 'journal items'
            elif search_type == 'sales_order':
                document_type = 'sales orders'
            elif search_type == 'purchase_order':
                document_type = 'purchase orders'
            elif search_type == 'purchase_request':
                document_type = 'purchase requests'
            else:
                document_type = 'records'
            raise UserError(_("No %s found for keywords: %s") % (document_type, ', '.join(keywords)))

        # Determine result title based on search type
        search_type = self.env.context.get('search_type', 'document')
        if search_type == 'bill':
            title = _('Bill Search Results: %s (%d found)') % (', '.join(keywords), len(record_ids))
        elif search_type == 'invoice':
            title = _('Invoice Search Results: %s (%d found)') % (', '.join(keywords), len(record_ids))
        elif search_type == 'journal_entry':
            title = _('Journal Entry Search Results: %s (%d found)') % (', '.join(keywords), len(record_ids))
        elif search_type == 'journal_items':
            title = _('Journal Items Search Results: %s (%d found)') % (', '.join(keywords), len(record_ids))
        elif search_type == 'sales_order':
            title = _('Sales Order Search Results: %s (%d found)') % (', '.join(keywords), len(record_ids))
        elif search_type == 'purchase_order':
            title = _('Purchase Order Search Results: %s (%d found)') % (', '.join(keywords), len(record_ids))
        elif search_type == 'purchase_request':
            title = _('Purchase Request Search Results: %s (%d found)') % (', '.join(keywords), len(record_ids))
        elif search_type == 'pos_comprehensive':
            title = _('POS Search Results: %s (%d found)') % (', '.join(keywords), len(record_ids))
        else:
            title = _('Search Results: %s (%d found)') % (', '.join(keywords), len(record_ids))

        # Return action
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'res_model': model_name,
            'view_mode': 'list,form', 
            'domain': [('id', 'in', record_ids)],
            'context': {'search_default_keywords': ', '.join(keywords)},
            'target': 'current',
        }

    def _search_pos_comprehensive(self, keywords):
        """Comprehensive POS search across multiple POS models"""
        all_results = []
        
        # Define POS models to search
        pos_models = {
            'pos.order': {
                'name': 'POS Orders',
                'fields': ['name', 'pos_reference', 'partner_id.name', 'user_id.name', 'session_id.name', 'config_id.name'],
                'title_field': 'name'
            },
            'pos.session': {
                'name': 'POS Sessions',
                'fields': ['name', 'user_id.name', 'config_id.name', 'state'],
                'title_field': 'name'
            },
            'pos.payment': {
                'name': 'POS Payments',
                'fields': ['name', 'pos_order_id.name', 'payment_method_id.name', 'partner_id.name'],
                'title_field': 'name'
            },
            'res.partner': {
                'name': 'POS Customers',
                'fields': ['name', 'email', 'phone', 'mobile', 'street', 'city'],
                'title_field': 'name',
                'extra_domain': [('customer_rank', '>', 0)]  # Only customers
            }
        }
        
        # Add pos_preparation_display.display if module exists
        try:
            if self.env['pos_preparation_display.display']:
                pos_models['pos_preparation_display.display'] = {
                    'name': 'Preparation Displays',
                    'fields': ['name', 'config_ids.name'],
                    'title_field': 'name'
                }
        except:
            pass  # Module not installed

        total_found = 0
        primary_results = []

        # Search in each POS model
        for model_name, config in pos_models.items():
            try:
                if not self.env[model_name].check_access_rights('read', raise_exception=False):
                    continue
                    
                all_record_ids = set()
                
                # Search for each keyword in each field
                for keyword in keywords:
                    for field in config['fields']:
                        try:
                            domain = [(field, 'ilike', keyword)]
                            
                            # Add extra domain if specified
                            if 'extra_domain' in config:
                                domain.extend(config['extra_domain'])
                            
                            records = self.env[model_name].search(domain, limit=20)
                            all_record_ids.update(records.ids)
                        except Exception:
                            continue
                
                if all_record_ids:
                    record_list = list(all_record_ids)[:20]  # Limit per model
                    records = self.env[model_name].browse(record_list)
                    
                    result_data = {
                        'model': model_name,
                        'model_name': config['name'],
                        'records': records,
                        'count': len(records),
                        'title_field': config['title_field']
                    }
                    
                    all_results.append(result_data)
                    total_found += len(records)
                    
                    # Prioritize POS Orders as primary results
                    if model_name == 'pos.order':
                        primary_results.append(result_data)
                        
            except Exception as e:
                print(f"Error searching in {model_name}: {e}")
                continue

        if not all_results:
            raise UserError(_("No POS records found for keywords: %s") % ', '.join(keywords))

        # Return results - prioritize POS Orders if found, otherwise first model
        if primary_results:
            first_result = primary_results[0]
        else:
            first_result = all_results[0]
        
        # Create comprehensive title
        model_summary = ', '.join([f"{r['model_name']} ({r['count']})" for r in all_results])
        
        return {
            'name': _('POS Search Results: %s | %s | Total: %d') % (
                ', '.join(keywords),
                model_summary,
                total_found
            ),
            'type': 'ir.actions.act_window',
            'res_model': first_result['model'],
            'view_mode': 'list,form',
            'domain': [('id', 'in', first_result['records'].ids)],
            'context': {
                'search_default_keywords': ', '.join(keywords),
                'search_results_summary': model_summary,
            },
            'target': 'current',
        }

    def _search_all_models(self, keywords):
        """Search across all supported models with multiple keywords"""
        all_results = []
        
        # Define search configurations for each model
        search_configs = {
            'account.move': {
                'name': 'Journal Entries/Invoices/Bills',
                'fields': ['name', 'ref', 'partner_id.name', 'invoice_origin', 'narration'],
                'extra_domain': []
            },
            'account.move.line': {
                'name': 'Journal Items',
                'fields': ['name', 'ref', 'partner_id.name', 'move_id.name', 'account_id.name'],
                'extra_domain': []
            },
            'pos.order': {
                'name': 'POS Orders',
                'fields': ['name', 'pos_reference', 'partner_id.name', 'user_id.name', 'session_id.name', 'config_id.name'],
                'extra_domain': []
            },
            'sale.order': {
                'name': 'Sales Orders',
                'fields': ['name', 'client_order_ref', 'partner_id.name', 'origin', 'user_id.name'],
                'extra_domain': []
            },
            'purchase.order': {
                'name': 'Purchase Orders',
                'fields': ['name', 'partner_ref', 'partner_id.name', 'origin', 'user_id.name', 'company_id.name'],
                'extra_domain': []
            },
            'purchase.request': {
                'name': 'Purchase Requests',
                'fields': ['name', 'description', 'requested_by.name', 'company_id.name', 'origin'],
                'extra_domain': []
            },
        }

        # Search in each model
        for model_name, config in search_configs.items():
            try:
                if not self.env[model_name].check_access_rights('read', raise_exception=False):
                    continue
                    
                all_record_ids = set()
                
                # Search for each keyword in each field
                for keyword in keywords:
                    for field in config['fields']:
                        try:
                            domain = [(field, 'ilike', keyword)]
                            domain.extend(config['extra_domain'])
                            
                            records = self.env[model_name].search(domain, limit=50)
                            all_record_ids.update(records.ids)
                        except Exception:
                            continue
                
                if all_record_ids:
                    record_list = list(all_record_ids)[:50]  # Limit to 50 records per model
                    records = self.env[model_name].browse(record_list)
                    all_results.append({
                        'model': model_name,
                        'model_name': config['name'],
                        'records': records,
                        'count': len(records)
                    })
                    
            except Exception as e:
                # Skip models that cause errors
                print(f"Error searching in {model_name}: {e}")
                continue

        if not all_results:
            raise UserError(_("No records found for keywords: %s") % ', '.join(keywords))

        # Return action to show results from the first model found
        return self._show_search_results(all_results, keywords)

    def _show_search_results(self, results, keywords):
        """Show search results in a custom view"""
        if results:
            first_result = results[0]
            return {
                'name': _('Search Results: %s (%d models, %d total records)') % (
                    ', '.join(keywords), 
                    len(results), 
                    sum(r['count'] for r in results)
                ),
                'type': 'ir.actions.act_window',
                'res_model': first_result['model'],
                'view_mode': 'list,form',
                'domain': [('id', 'in', first_result['records'].ids)],
                'context': {'search_default_keywords': ', '.join(keywords)},
                'target': 'current',
            }

    def action_discard(self):
        """Close the wizard without action"""
        return {'type': 'ir.actions.act_window_close'}