from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FuelTankReplenishment(models.Model):
    _name = 'fuel.tank.replenishment'
    _description = 'Tank Replenishment'
    _order = 'date desc, id desc'

    date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
        required=True,
        readonly=True,
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('done', 'Confirmed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        readonly=True,
        copy=False,
    )

    receipt_id = fields.Many2one(
        'stock.picking',
        string='Validated Receipt',
        required=True,
        ondelete='restrict',
        domain=[
            ('state', '=', 'done'),
            ('picking_type_code', '=', 'incoming'),
            ('fuel_replenished', '=', False),
        ],
    )

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        compute='_compute_receipt_data',
        readonly=True,
        store=True,
    )

    product_id = fields.Many2one(
        'product.product',
        string='Fuel Product',
        compute='_compute_receipt_data',
        readonly=True,
        store=True,
    )

    received_qty = fields.Float(
        string='Received Quantity (L)',
        related='receipt_id.fuel_received_qty',
        readonly=True,
        digits=(16, 3),
    )

    already_replenished_qty = fields.Float(
        string='Already Replenished',
        related='receipt_id.fuel_replenished_qty',
        readonly=True,
        digits=(16, 3),
    )

    remaining_qty = fields.Float(
        string='Remaining Quantity',
        related='receipt_id.fuel_remaining_qty',
        readonly=True,
        digits=(16, 3),
    )

    tank_id = fields.Many2one(
        'fuel.tank',
        string='Tank',
        required=True,
        ondelete='restrict',
    )

    station_id = fields.Many2one(
        'fuel.station',
        related='tank_id.station_id',
        string='Station',
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        'res.company',
        related='station_id.company_id',
        string='Company',
        store=True,
        index=True,
        readonly=True,
    )

    shift_id = fields.Many2one(
        'fuel.shift',
        string='Shift',
        required=True,
        ondelete='restrict',
        domain="[('station_id', '=', station_id), ('state', '=', 'open')]",
    )

    quantity = fields.Float(
        string='Quantity to Replenish (L)',
        required=True,
        digits=(16, 3),
    )

    remaining_after_qty = fields.Float(
        string='Remaining After Replenishment (L)',
        readonly=True,
        copy=False,
        digits=(16, 3),
    )

    user_id = fields.Many2one(
        'res.users',
        string='Recorded By',
        default=lambda self: self.env.user,
        readonly=True,
    )

    confirmed_by = fields.Many2one(
        'res.users',
        string='Confirmed By',
        readonly=True,
        copy=False,
    )

    confirmed_date = fields.Datetime(
        string='Confirmed On',
        readonly=True,
        copy=False,
    )

    cancelled_by = fields.Many2one(
        'res.users',
        string='Cancelled By',
        readonly=True,
        copy=False,
    )

    cancelled_date = fields.Datetime(
        string='Cancelled On',
        readonly=True,
        copy=False,
    )

    cancel_reason = fields.Text(
        string='Cancellation Reason',
        copy=False,
    )

    notes = fields.Text(
        string='Notes',
    )

    @api.depends('receipt_id')
    def _compute_receipt_data(self):
        for rec in self:
            rec.purchase_order_id = False
            rec.product_id = False

            picking = rec.receipt_id

            if not picking or picking.state != 'done':
                continue

            # Retrouver la commande d'achat liée à la réception
            purchase_lines = picking.move_ids.mapped('purchase_line_id')
            purchase_orders = purchase_lines.mapped('order_id')

            if len(purchase_orders) == 1:
                rec.purchase_order_id = purchase_orders.id

            # Mouvements réellement réceptionnés
            moves = picking.move_ids.filtered(
                lambda move:
                    move.state == 'done'
                    and move.product_id
                    and move.quantity > 0
            )

            products = moves.mapped('product_id')

            # Pour le moment :
            # une réception carburant = un seul produit
            if len(products) == 1:
                rec.product_id = products.id

    @api.onchange('receipt_id')
    def _onchange_receipt_id(self):
        self.tank_id = False
        self.shift_id = False
        self.quantity = 0.0

    def action_confirm(self):
        self.ensure_one()
        if self.shift_id.state != 'open':
            raise UserError(_(
                "A replenishment can only be confirmed on an open shift."
            ))

        # Empêcher une deuxième confirmation
        if self.state == 'done':
            raise UserError(_(
                'This replenishment has already been confirmed.'
            ))

        if not self.receipt_id:
            raise UserError(_(
                'Please select a validated receipt.'
            ))

        if self.receipt_id.state != 'done':
            raise UserError(_(
                'Only a validated receipt can be used.'
            ))

        # La réception disparaît uniquement lorsque tout est réparti
        if self.receipt_id.fuel_replenished:
            raise UserError(_(
                'This receipt has been fully replenished '
                'and cannot be used again.'
            ))

        if self.quantity <= 0:
            raise UserError(_(
                'The quantity to replenish must be positive.'
            ))

        if not self.product_id:
            raise UserError(_(
                'No fuel product could be identified '
                'on the selected receipt.'
            ))

        if not self.tank_id:
            raise UserError(_(
                'Please select a tank.'
            ))

        # Vérifier que le produit de la cuve correspond à la réception
        if self.tank_id.product_id != self.product_id:
            raise UserError(_(
                "Tank '%(tank)s' contains '%(tank_product)s', "
                "but the receipt contains '%(receipt_product)s'.",
                tank=self.tank_id.display_name,
                tank_product=self.tank_id.product_id.display_name,
                receipt_product=self.product_id.display_name,
            ))

        # Quantité encore réellement disponible sur la réception
        remaining_qty = self.receipt_id.fuel_remaining_qty

        if remaining_qty <= 0:
            raise UserError(_(
                'There is no remaining quantity available '
                'on this receipt.'
            ))

        if self.quantity > remaining_qty:
            raise UserError(_(
                "The quantity to replenish cannot exceed "
                "the remaining quantity.\n\n"
                "Received: %(received).3f L\n"
                "Already replenished: %(used).3f L\n"
                "Remaining: %(remaining).3f L\n"
                "Entered: %(entered).3f L",
                received=self.receipt_id.fuel_received_qty,
                used=self.receipt_id.fuel_replenished_qty,
                remaining=remaining_qty,
                entered=self.quantity,
            ))

        # Ajouter le carburant dans la cuve
        self.tank_id._adjust_stock(self.quantity)

        # Quantité totale déjà répartie depuis cette réception
        new_replenished_qty = (
            self.receipt_id.fuel_replenished_qty
            + self.quantity
        )

        # Quantité restante après cette opération
        remaining_after = max(
            self.receipt_id.fuel_received_qty
            - new_replenished_qty,
            0.0,
        )

        # Mettre à jour la réception
        self.receipt_id.write({
            'fuel_replenished_qty': new_replenished_qty,
            'fuel_replenished': remaining_after <= 0.000001,
        })

        # Garder l'historique exact de cette opération
        self.write({
            'remaining_after_qty': remaining_after,
            'state': 'done',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_cancel(self):
        self.ensure_one()
        if self.shift_id.state == 'validated' or self.shift_id.stock_posted:
            raise UserError(_(
                "A replenishment linked to a validated shift cannot be cancelled."
            ))

        if self.state != 'done':
            raise UserError(_(
                'Only a confirmed replenishment can be cancelled.'
            ))

        if not self.cancel_reason:
            raise UserError(_(
                'Please enter a cancellation reason.'
            ))

        # Vérifier qu'on peut retirer la quantité de la cuve
        if self.tank_id.current_stock < self.quantity:
            raise UserError(_(
                "This replenishment cannot be cancelled because the tank "
                "no longer contains enough stock.\n\n"
                "Tank stock: %(stock).3f L\n"
                "Quantity to reverse: %(quantity).3f L",
                stock=self.tank_id.current_stock,
                quantity=self.quantity,
            ))

        # 1. Annuler l'effet sur la cuve
        self.tank_id._adjust_stock(-self.quantity)

        # 2. Annuler l'effet sur la réception fournisseur
        new_replenished_qty = max(
            self.receipt_id.fuel_replenished_qty - self.quantity,
            0.0,
        )

        new_remaining_qty = max(
            self.receipt_id.fuel_received_qty - new_replenished_qty,
            0.0,
        )

        self.receipt_id.write({
            'fuel_replenished_qty': new_replenished_qty,
            'fuel_replenished': new_remaining_qty <= 0.000001,
        })

        # 3. Conserver la trace de l'annulation
        self.write({
            'state': 'cancelled',
            'cancelled_by': self.env.user.id,
            'cancelled_date': fields.Datetime.now(),
        })

        return True

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_(
                    'Only draft replenishments can be deleted. '
                    'A confirmed replenishment must be cancelled instead.'
                ))

        return super().unlink()