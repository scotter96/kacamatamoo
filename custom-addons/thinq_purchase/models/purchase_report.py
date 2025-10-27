from odoo import api, fields, models
from odoo.tools.sql import SQL


class PurchaseReport(models.Model):
    _inherit = 'purchase.report'

    qty_scrapped = fields.Float('Qty Scrapped', readonly=True)
    fulfillment_percentage = fields.Integer('Fulfillment (%)', readonly=True, aggregator='avg',
                                            help="Percentage of ordered quantity that has been received")
    qc_passed_percentage = fields.Integer('QC Passed (%)', readonly=True, aggregator='avg',
                                          help="Percentage of ordered quantity that passed QC")

    def _select(self) -> SQL:
        base_select = super()._select()
        extra_select = SQL(
            """,
                    SUM(l.scrapped_qty / line_uom.factor * product_uom.factor) as qty_scrapped,
                    CASE
                        WHEN SUM(l.product_qty / line_uom.factor * product_uom.factor) > 0
                        THEN ROUND((SUM(l.qty_received / line_uom.factor * product_uom.factor) / SUM(l.product_qty / line_uom.factor * product_uom.factor)) * 100)
                        ELSE 0
                    END as fulfillment_percentage,
                    CASE
                        WHEN SUM(l.product_qty / line_uom.factor * product_uom.factor) > 0
                        THEN ROUND(((SUM(l.qty_received / line_uom.factor * product_uom.factor) - SUM(l.scrapped_qty / line_uom.factor * product_uom.factor)) / SUM(l.product_qty / line_uom.factor * product_uom.factor)) * 100)
                        ELSE 0
                    END as qc_passed_percentage
            """
        )
        return SQL("%s %s", base_select, extra_select)
