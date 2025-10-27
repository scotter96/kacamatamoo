# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountAsset(models.Model):
    _inherit = 'account.asset'
    asset_code = fields.Char('Asset Code', tracking=True)

    ga_asset_category_id = fields.Many2one(
        'ga.asset.category',
        string='GA Asset Category',
        ondelete='set null',
        help="Kategori aset menurut GA",
        tracking=True
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        help="Departemen pengguna aset",
        tracking=True
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Department (Analytic)',
        help="Departemen pengguna aset, terhubung ke Analytic Account",
        tracking=True
    )

    year_of_purchase = fields.Integer(
        string='Year of Purchase',
        help="Tahun pembelian aset",
        tracking=True
    )

    month_of_purchase = fields.Integer(
        string='Month of Purchase',
        help="Bulan pembelian aset (1-12)",
        tracking=True
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='User Employee ID (OLD)',
        help="Karyawan yang menggunakan aset",
    )

    employee_id_char = fields.Char(
        string='User Employee ID',
        help="ID karyawan yang menggunakan aset",
        tracking=True
    )

    employee_name = fields.Char(
        string='User Employee Name',
        help="Nama karyawan yang menggunakan aset",
        tracking=True
    )

    asset_conditions = fields.Text(
        string='Asset Condition',
        tracking=True
    )

    ga_asset_attribute_ids = fields.One2many(
        'ga.asset.attribute.line',
        'asset_id',
        string='GA Asset Attributes'
    )

    tax_class = fields.Selection([
        ('class_1', 'Kelas I'),
        ('class_2', 'Kelas II'),
        ('class_3', 'Kelas III'),
        ('class_4', 'Kelas IV'),
    ], string='Tax Class',
        help="Kategori pajak menurut Dirjen Pajak"
    )

    additional_notes = fields.Text(
        string='Additional Notes',
        help="Catatan tambahan tentang aset"
    )
    
    @api.constrains('asset_code')
    def _check_asset_code_unique(self):
        """Memastikan asset_code tidak duplikat"""
        for record in self:
            if record.asset_code:
                # Cari asset lain dengan asset_code yang sama
                existing_asset = self.search([
                    ('asset_code', '=', record.asset_code),
                    ('id', '!=', record.id)
                ])
                if existing_asset:
                    raise ValidationError(
                        _('Asset Code "%s" already exists in asset "%s". Asset Code must be unique.') 
                        % (record.asset_code, existing_asset[0].name)
                    )