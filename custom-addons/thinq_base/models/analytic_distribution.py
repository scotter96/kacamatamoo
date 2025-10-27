# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare

import logging

_logger = logging.getLogger(__name__)


class AnalyticMixin(models.AbstractModel):
    _inherit = 'analytic.mixin'

    @api.constrains('analytic_distribution')
    def _check_analytic_distribution_percentage(self):
        """Validate that analytic distribution percentage does not exceed 100%"""
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        
        for record in self:
            if not record.analytic_distribution:
                continue
                
            total_percentage = 0.0
            distribution_by_plan = {}
            
            # Group by analytic plan to validate each plan separately
            for analytic_account_ids, percentage in record.analytic_distribution.items():
                try:
                    # Convert percentage to float if it's string
                    if isinstance(percentage, str):
                        percentage = float(percentage)
                    
                    # Get analytic accounts
                    account_ids = [int(acc_id) for acc_id in analytic_account_ids.split(',') if acc_id.strip()]
                    analytic_accounts = self.env['account.analytic.account'].browse(account_ids).exists()
                    
                    for account in analytic_accounts:
                        plan_id = account.plan_id.id if account.plan_id else 'no_plan'
                        
                        # Initialize plan percentage if not exists
                        if plan_id not in distribution_by_plan:
                            distribution_by_plan[plan_id] = 0.0
                        
                        # Add percentage to plan total
                        distribution_by_plan[plan_id] += percentage
                        
                        _logger.debug(f"Account: {account.name}, Plan: {account.plan_id.name if account.plan_id else 'No Plan'}, Percentage: {percentage}, Plan Total: {distribution_by_plan[plan_id]}")
                    
                    # Also track total percentage across all plans
                    total_percentage += percentage
                    
                except (ValueError, TypeError) as e:
                    _logger.error(f"Error processing analytic distribution: {e}")
                    raise ValidationError(_("Invalid analytic distribution format. Please check your percentage values."))
            
            # Validate each plan separately
            for plan_id, plan_percentage in distribution_by_plan.items():
                if float_compare(plan_percentage, 100.0, precision_digits=decimal_precision) > 0:
                    if plan_id == 'no_plan':
                        plan_name = _("Accounts without plan")
                    else:
                        plan = self.env['account.analytic.plan'].browse(plan_id)
                        plan_name = plan.name if plan.exists() else _("Unknown Plan")
                    
                    raise ValidationError(_(
                        "Analytic Distribution validation failed!\n"
                        "Total percentage: %(percentage).2f%%\n"
                        "Maximum allowed: 100.00%%\n"
                        "Please adjust the distribution percentages."
                    ) % {
                        'plan_name': plan_name,
                        'percentage': plan_percentage
                    })
            
    
    def _validate_analytic_distribution_total(self):
        """Additional method to validate total distribution if needed"""
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        
        for record in self:
            if not record.analytic_distribution:
                continue
            
            total_percentage = sum(
                float(percentage) if isinstance(percentage, str) else percentage
                for percentage in record.analytic_distribution.values()
            )
            
            if float_compare(total_percentage, 100.0, precision_digits=decimal_precision) > 0:
                raise ValidationError(_(
                    "Total Analytic Distribution cannot exceed 100%%!\n"
                    "Current total: %.2f%%\n"
                    "Please adjust the percentages."
                ) % total_percentage)

    @api.onchange('analytic_distribution')
    def _onchange_analytic_distribution(self):
        """Provide real-time feedback when editing analytic distribution"""
        if not self.analytic_distribution:
            return
        
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        distribution_by_plan = {}
        
        try:
            for analytic_account_ids, percentage in self.analytic_distribution.items():
                # Convert percentage to float if it's string
                if isinstance(percentage, str):
                    percentage = float(percentage)
                
                # Get analytic accounts
                account_ids = [int(acc_id) for acc_id in analytic_account_ids.split(',') if acc_id.strip()]
                analytic_accounts = self.env['account.analytic.account'].browse(account_ids).exists()
                
                for account in analytic_accounts:
                    plan_id = account.plan_id.id if account.plan_id else 'no_plan'
                    
                    if plan_id not in distribution_by_plan:
                        distribution_by_plan[plan_id] = 0.0
                    
                    distribution_by_plan[plan_id] += percentage
            
            # Check each plan and show warning if > 100%
            for plan_id, plan_percentage in distribution_by_plan.items():
                if float_compare(plan_percentage, 100.0, precision_digits=decimal_precision) > 0:
                    if plan_id == 'no_plan':
                        plan_name = _("Accounts without plan")
                    else:
                        plan = self.env['account.analytic.plan'].browse(plan_id)
                        plan_name = plan.name if plan.exists() else _("Unknown Plan")
                    
                    return {
                        'warning': {
                            'title': _("Analytic Distribution Warning"),
                            'message': _(
                                "Total analytic distribution has %(percentage).2f%%.\n"
                                "This exceeds the maximum allowed 100%%."
                            ) % {
                                'plan_name': plan_name,
                                'percentage': plan_percentage
                            }
                        }
                    }
        
        except (ValueError, TypeError) as e:
            _logger.warning(f"Error in onchange analytic distribution: {e}")
            return {
                'warning': {
                    'title': _("Invalid Input"),
                    'message': _("Please enter valid percentage values.")
                }
            }