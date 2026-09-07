from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FuelMeterCorrectionWizard(models.TransientModel):
    _name = 'fuel.meter.correction.wizard'
    _description = 'Meter Closing Index Correction'

    shift_id = fields.Many2one(
        'fuel.shift',
        string='Shift',
        required=True,
        readonly=True,
    )
    reading_id = fields.Many2one(
        'fuel.meter.reading',
        string='Meter Reading',
        required=True,
        domain="[('shift_id', '=', shift_id)]",
    )
    opening_reading = fields.Float(
        related='reading_id.opening_reading',
        string='Opening Index',
        readonly=True,
    )

    old_closing_reading = fields.Float(
        related='reading_id.closing_reading',
        string='Current Closing Index',
        readonly=True,
    )

    old_dispensed_qty = fields.Float(
        related='reading_id.dispensed_qty',
        string='Current Dispensed Quantity',
        readonly=True,
    )

    new_closing_reading = fields.Float(
        string='Corrected Closing Index',
        required=True,
        digits=(16, 3),
    )

    new_dispensed_qty = fields.Float(
        string='Corrected Dispensed Quantity',
        compute='_compute_correction',
        digits=(16, 3),
    )

    stock_adjustment_qty = fields.Float(
        string='Stock Adjustment',
        compute='_compute_correction',
        digits=(16, 3),
    )

    reason = fields.Text(
        string='Correction Reason',
        required=True,
    )

    @api.depends(
        'reading_id',
        'new_closing_reading',
    )
    def _compute_correction(self):
        for rec in self:
            if not rec.reading_id:
                rec.new_dispensed_qty = 0.0
                rec.stock_adjustment_qty = 0.0
                continue

            new_dispensed = max(
                0.0,
                rec.new_closing_reading - rec.reading_id.opening_reading,
            )

            rec.new_dispensed_qty = new_dispensed

            rec.stock_adjustment_qty = (rec.reading_id.dispensed_qty - new_dispensed)

    def action_confirm(self):
        self.ensure_one()

        reading = self.reading_id
        shift = reading.shift_id

        # Le shift doit toujours être validé
        if shift.state != 'validated' or not shift.stock_posted:
            raise UserError(_(
                "This meter reading no longer belongs to a validated shift."
            ))

        # Le nouvel index ne peut pas être inférieur à l'ouverture
        if self.new_closing_reading < reading.opening_reading:
            raise UserError(_(
                "The corrected closing index cannot be lower than "
                "the opening index."
            ))

        # Il doit réellement y avoir une correction
        if abs(
            self.new_closing_reading - reading.closing_reading
        ) <= 0.000001:
            raise UserError(_(
                "The corrected closing index is identical to the current index."
            ))

        # Chercher un éventuel shift validé plus récent
        later_candidates = self.env['fuel.meter.reading'].search([
            ('nozzle_id', '=', reading.nozzle_id.id),
            ('shift_id.state', '=', 'validated'),
            ('shift_date', '>=', reading.shift_date),
            ('id', '!=', reading.id),
        ], order='shift_date asc, id asc')

        later_validated = later_candidates.filtered(
            lambda r:
                r.shift_date > reading.shift_date
                or (
                    r.shift_date == reading.shift_date
                    and r.id > reading.id
                )
        )

        if later_validated:
            raise UserError(_(
                "This closing index cannot be corrected because a later "
                "validated shift already exists for this nozzle. "
                "A stock regularization must be used instead."
            ))

        old_closing = reading.closing_reading
        old_dispensed = reading.dispensed_qty
        old_total = reading.total_amount

        new_dispensed = max(
            0.0,
            self.new_closing_reading - reading.opening_reading,
        )

        new_total = (
            new_dispensed
            * reading.unit_price
        )

        stock_adjustment = (
            old_dispensed
            - new_dispensed
        )

        # Si la correction doit encore retirer du stock
        if (
            stock_adjustment < 0
            and reading.tank_id.current_stock < abs(stock_adjustment)
        ):
            raise UserError(_(
                "The correction requires more fuel to be removed from the tank, "
                "but the available stock is insufficient.\n\n"
                "Available stock: %(stock).3f L\n"
                "Additional quantity required: %(qty).3f L",
                stock=reading.tank_id.current_stock,
                qty=abs(stock_adjustment),
            ))

        # Corriger le Meter Reading validé
        reading._apply_validated_closing_correction(
            self.new_closing_reading
        )

        # Corriger le stock de la cuve
        if abs(stock_adjustment) > 0.000001:
            reading.tank_id._adjust_stock(
                stock_adjustment
            )

        # Chercher le prochain relevé NON validé du même pistolet
        next_candidates = self.env['fuel.meter.reading'].search([
            ('nozzle_id', '=', reading.nozzle_id.id),
            ('shift_id.state', 'in', ['draft', 'open']),
            ('shift_date', '>=', reading.shift_date),
            ('id', '!=', reading.id),
        ], order='shift_date asc, id asc')

        next_reading = next_candidates.filtered(
            lambda r:
                r.shift_date > reading.shift_date
                or (
                    r.shift_date == reading.shift_date
                    and r.id > reading.id
                )
        )[:1]

        # Synchroniser son opening si nécessaire
        if next_reading:
            next_reading._sync_opening_after_correction(
                self.new_closing_reading
            )

        # Enregistrer l'historique permanent
        self.env['fuel.meter.correction'].create({
            'reading_id': reading.id,
            'old_closing_reading': old_closing,
            'new_closing_reading': self.new_closing_reading,
            'old_dispensed_qty': old_dispensed,
            'new_dispensed_qty': new_dispensed,
            'stock_adjustment_qty': stock_adjustment,
            'old_total_amount': old_total,
            'new_total_amount': new_total,
            'reason': self.reason,
        })

        # Ajouter une trace dans le chatter du shift
        shift.message_post(
            body=_(
                "Closing index corrected for nozzle '%(nozzle)s': "
                "%(old).3f L → %(new).3f L. "
                "Stock adjustment: %(adjustment).3f L.",
                nozzle=reading.nozzle_id.display_name,
                old=old_closing,
                new=self.new_closing_reading,
                adjustment=stock_adjustment,
            )
        )

        return {
            'type': 'ir.actions.act_window_close'
        }