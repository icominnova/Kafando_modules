from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fuel_purchase_type = fields.Selection(
        related='purchase_id.purchase_type',
        string='Purchase Type',
        store=True,
        readonly=True,
    )

    fuel_station_id = fields.Many2one(
        'fuel.station',
        related='purchase_id.fuel_station_id',
        string='Fuel Station',
        store=True,
        readonly=True,
    )

    fuel_replenished = fields.Boolean(
        string='Fully Replenished',
        default=False,
        copy=False,
        readonly=True,
        help='The full received quantity has been transferred to fuel tanks.',
    )

    fuel_received_qty = fields.Float(
        string='Received Fuel Quantity',
        compute='_compute_fuel_quantities',
        store=True,
        readonly=True,
        digits=(16, 3),
    )

    fuel_replenished_qty = fields.Float(
        string='Replenished Quantity',
        default=0.0,
        copy=False,
        readonly=True,
        digits=(16, 3),
    )

    fuel_remaining_qty = fields.Float(
        string='Remaining Quantity',
        compute='_compute_fuel_quantities',
        store=True,
        readonly=True,
        digits=(16, 3),
    )

    @api.depends(
        'move_ids.state',
        'move_ids.quantity',
        'move_ids.product_id',
        'move_ids.product_uom',
        'fuel_replenished_qty',
    )
    def _compute_fuel_quantities(self):
        for picking in self:
            received_qty = 0.0

            moves = picking.move_ids.filtered(
                lambda m:
                    m.state == 'done'
                    and m.product_id
                    and m.quantity > 0
            )

            products = moves.mapped('product_id')

            if len(products) == 1:
                product = products[0]

                received_qty = sum(
                    move.product_uom._compute_quantity(
                        move.quantity,
                        product.uom_id,
                    )
                    for move in moves
                )

            picking.fuel_received_qty = received_qty

            picking.fuel_remaining_qty = max(
                received_qty - picking.fuel_replenished_qty,
                0.0,
            )