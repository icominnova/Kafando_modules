from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fuel_replenished = fields.Boolean(
        string='Fuel Replenished',
        default=False,
        copy=False,
        readonly=True,
        help='Indicates that this receipt has already been transferred to a fuel tank.',
    )