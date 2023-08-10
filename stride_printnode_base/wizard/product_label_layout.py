# Copyright 2021 VentorTech OU
# See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class ProductLabelLayout(models.TransientModel):
    _name = 'product.label.layout'
    _inherit = ['product.label.layout', 'printnode.label.layout.mixin']

    def process(self):
        self.ensure_one()

        if self.picking_quantity == 'custom_per_product':
            self._check_quantity()

        # Download PDF if no printer selected
        if not self.printer_id:
            # Update context to download on client side instead of printing
            # Check action_service.js file for details
            return super(ProductLabelLayout, self.with_context(download_only=True)).process()

        xml_id, data = self._prepare_report_data()

        if not xml_id:
            raise UserError(_('Unable to find report template for %s format', self.print_format))

        return self.env.ref(xml_id).with_context(
            printer_id=self.printer_id.id,
            printer_bin=self.printer_bin.id
        ).report_action(None, data=data)

    def _check_quantity(self):
        for rec in self.product_line_ids:
            if rec.quantity < 1:
                raise ValidationError(
                    _(
                        'Quantity can not be less than 1 for product {product}'
                    ).format(**{
                        'product': rec.product_id.display_name or rec.product_tmpl_id.display_name,
                    })
                )


class ProductLabelLayoutLine(models.TransientModel):
    _name = 'product.label.layout.line'
    _description = 'Choose the sheet layout to print the labels / Line'

    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Product (Template)',
    )

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
    )

    quantity = fields.Integer(
        required=True,
        default=1,
    )

    wizard_id = fields.Many2one(
        comodel_name='product.label.layout',
    )
