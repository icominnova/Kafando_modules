# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    product_qty_available = fields.Float(
        string="Stock dispo.",
        compute="_compute_product_qty_available",
        digits="Product Unit of Measure",
        readonly=True,
        help="Quantité physique disponible pour ce produit dans l'entrepôt du devis.",
    )

    @api.depends("product_id", "order_id.warehouse_id")
    def _compute_product_qty_available(self):
        for line in self:
            if not line.product_id:
                line.product_qty_available = 0.0
                continue

            product = line.product_id
            if line.order_id.warehouse_id:
                product = product.with_context(warehouse=line.order_id.warehouse_id.id)
            line.product_qty_available = product.qty_available
