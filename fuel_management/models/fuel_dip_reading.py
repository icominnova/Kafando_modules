from odoo import models, fields, api, _
from odoo.exceptions import UserError

class FuelDipReading(models.Model):
    _name = 'fuel.dip.reading'
    _description = 'Tank Dip Reading'
    _rec_name = 'tank_id'

    shift_id = fields.Many2one('fuel.shift', string='Shift', required=True, ondelete='cascade')
    station_id = fields.Many2one('fuel.station', related='shift_id.station_id', store=True)
    tank_id = fields.Many2one('fuel.tank', string='Tank', required=True,
        domain="[('station_id', '=', station_id)]")
    product_id = fields.Many2one('product.product', related='tank_id.product_id', store=True, string='Product')

    opening_level = fields.Float(
        string='Opening Level (L)', 
        digits=(16, 3),
    )
    received_qty = fields.Float(
        string='Received During Shift (L)',
        compute='_compute_received_qty',
        store=True,
        digits=(16, 3),
        readonly=True,
    )
    closing_level = fields.Float(
        string='Closing Level (L)', 
        digits=(16, 3),
    )
    expected_closing = fields.Float(
        string='Expected Closing (L)', 
        compute='_compute_expected', 
        store=True, digits=(16, 3),
    )
    variance = fields.Float(
        string='Variance (L)', 
        compute='_compute_variance', 
        store=True, digits=(16, 3),
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        related='station_id.company_id',
        string='Company',
        store=True,
        index=True,
        readonly=True,
    )

    @api.depends(
    'tank_id',
    'shift_id.replenishment_ids.quantity',
    'shift_id.replenishment_ids.state',
    'shift_id.replenishment_ids.tank_id',
)
    def _compute_received_qty(self):
        for rec in self:
            if not rec.shift_id or not rec.tank_id:
                rec.received_qty = 0.0
                continue
            replenishments = rec.shift_id.replenishment_ids.filtered(
                lambda r:
                    r.tank_id == rec.tank_id
                    and r.state == 'done'
            )
            rec.received_qty = sum(
                replenishments.mapped('quantity')
            )
    
    @api.depends(
    'opening_level',
    'received_qty',
    'tank_id',
    'shift_id.meter_reading_ids.dispensed_qty',
    )
    def _compute_expected(self):
        for rec in self:
            readings = rec.shift_id.meter_reading_ids.filtered(
                lambda r: r.tank_id == rec.tank_id
            )

            dispensed = sum(readings.mapped('dispensed_qty'))

            rec.expected_closing = (
                rec.opening_level
                + rec.received_qty
                - dispensed
            )

    @api.depends('expected_closing', 'closing_level')
    def _compute_variance(self):
        for rec in self:
            rec.variance = rec.closing_level - rec.expected_closing

    def write(self, vals):
        for rec in self:
            if rec.shift_id.state == 'validated' or rec.shift_id.stock_posted:
                raise UserError(_(
                    "You cannot modify a dip reading from a validated shift."
                ))

        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            shift_id = vals.get('shift_id')

            if shift_id:
                shift = self.env['fuel.shift'].browse(shift_id)

                if shift.state == 'validated' or shift.stock_posted:
                    raise UserError(_(
                        "You cannot add a dip reading to a validated shift."
                    ))

        return super().create(vals_list)

    def unlink(self):
        for rec in self:
            if rec.shift_id.state == 'validated' or rec.shift_id.stock_posted:
                raise UserError(_(
                    "You cannot delete a dip reading from a validated shift."
                ))

        return super().unlink()
