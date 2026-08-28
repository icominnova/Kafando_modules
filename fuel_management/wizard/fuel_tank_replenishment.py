from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FuelTankReplenishment(models.TransientModel):
    _name = 'fuel.tank.replenishment'
    _description = 'Tank Replenishment'

    receipt_id = fields.Many2one(
        'stock.picking',
        string='Validated Receipt',
        required=True,
        domain=[
            ('state', '=', 'done'),
            ('picking_type_code', '=', 'incoming'),
        ],
    )

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        compute='_compute_receipt_data',
        readonly=True,
    )

    product_id = fields.Many2one(
        'product.product',
        string='Fuel Product',
        compute='_compute_receipt_data',
        readonly=True,
    )

    received_qty = fields.Float(
        string='Received Quantity (L)',
        compute='_compute_receipt_data',
        readonly=True,
        digits=(16, 3),
    )

    tank_id = fields.Many2one(
        'fuel.tank', 
        string='Tank', 
        required=True,
    )

    station_id = fields.Many2one(
        related='tank_id.station_id', 
        string='Station',
        readonly=True,
    )

    shift_id = fields.Many2one(
        'fuel.shift', 
        string='Shift', 
        required=True,
        domain="[('station_id', '=', station_id), ('state', '=', 'open')]",
    )

    quantity = fields.Float(
        string='Quantity Received (L)', 
        required=True,
        digits=(16, 3),
    )

    @api.depends('receipt_id')
    def _compute_receipt_data(self):
        for rec in self:
            rec.purchase_order_id = False
            rec.product_id = False
            rec.received_qty = 0.0

            picking = rec.receipt_id

            if not picking or picking.state != 'done':
                continue

            # Retrouver la commande d'achat
            purchase_lines = picking.move_ids.mapped('purchase_line_id')
            purchase_orders = purchase_lines.mapped('order_id')

            if len(purchase_orders) == 1:
                rec.purchase_order_id = purchase_orders.id

            # Mouvements réellement validés
            moves = picking.move_ids.filtered(
                lambda m:
                    m.state == 'done'
                    and m.product_id
                    and m.quantity > 0
            )

            products = moves.mapped('product_id')

            # Pour l'instant : une réception Fuel = un produit carburant
            if len(products) == 1:
                product = products

                rec.product_id = product.id

                qty = 0.0

                for move in moves:
                    qty += move.product_uom._compute_quantity(
                        move.quantity,
                        product.uom_id,
                    )

                rec.received_qty = qty

    @api.onchange('receipt_id')
    def _onchange_receipt_id(self):
        self.tank_id = False
        self.shift_id = False
        self.quantity = 0.0

    def action_confirm(self):
        self.ensure_one()

        if not self.receipt_id:
            raise UserError(_(
                'Please select a validated receipt.'
            ))

        if self.receipt_id.state != 'done':
            raise UserError(_(
                'Only a validated receipt can be used.'
            ))

        if self.quantity <= 0:
            raise UserError(_(
                'The received quantity must be positive.'
            ))

        if not self.product_id:
            raise UserError(_(
                'No fuel product could be identified '
                'on the selected receipt.'
            ))

        if self.tank_id.product_id != self.product_id:
            raise UserError(_(
                "Tank '%(tank)s' contains '%(tank_product)s', "
                "but the receipt contains '%(receipt_product)s'.",
                tank=self.tank_id.display_name,
                tank_product=self.tank_id.product_id.display_name,
                receipt_product=self.product_id.display_name,
            ))

        if self.quantity > self.received_qty:
            raise UserError(_(
                "The quantity to replenish cannot exceed "
                "the quantity received.\n\n"
                "Received: %(received).3f L\n"
                "Entered: %(entered).3f L",
                received=self.received_qty,
                entered=self.quantity,
            ))

        dip_reading = self.env['fuel.dip.reading'].search([
            ('tank_id', '=', self.tank_id.id),
            ('shift_id', '=', self.shift_id.id),
        ], limit=1)

        if not dip_reading:
            raise UserError(_(
                "Cannot replenish: no dip reading found for tank "
                "'%(tank)s' on shift '%(shift)s'.",
                tank=self.tank_id.name,
                shift=self.shift_id.name,
            ))

        self.tank_id._adjust_stock(self.quantity)

        dip_reading.received_qty += self.quantity

        return {
            'type': 'ir.actions.act_window_close'
        }