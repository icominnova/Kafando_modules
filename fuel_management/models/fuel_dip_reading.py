from odoo import models, fields, api

class FuelDipReading(models.Model):
    _name = 'fuel.dip.reading'
    _description = 'Tank Dip Reading'
    _rec_name = 'tank_id'

    shift_id = fields.Many2one('fuel.shift', string='Shift', required=True, ondelete='cascade')
    station_id = fields.Many2one('fuel.station', related='shift_id.station_id', store=True)
    tank_id = fields.Many2one('fuel.tank', string='Tank', required=True,
        domain="[('station_id', '=', station_id)]")
    product_id = fields.Many2one('product.product', related='tank_id.product_id', store=True, string='Product')

    opening_level = fields.Float(string='Opening Level (L)', digits=(16, 3))
    received_qty = fields.Float(string='Received During Shift (L)', digits=(16, 3))
    closing_level = fields.Float(string='Closing Level (L)', digits=(16, 3))
    expected_closing = fields.Float(string='Expected Closing (L)', compute='_compute_expected', store=True, digits=(16, 3))
    variance = fields.Float(string='Variance (L)', compute='_compute_variance', store=True, digits=(16, 3))
    notes = fields.Text(string='Notes')

    @api.depends('opening_level', 'received_qty', 'shift_id', 'product_id')
    def _compute_expected(self):
        for rec in self:
            # Expected = opening + received - dispensed (from meter readings of same product/shift)
            dispensed = sum(
                self.env['fuel.meter.reading'].search([
                    ('shift_id', '=', rec.shift_id.id),
                    ('product_id', '=', rec.product_id.id),
                ]).mapped('dispensed_qty')
            )
            rec.expected_closing = rec.opening_level + rec.received_qty - dispensed

    @api.depends('expected_closing', 'closing_level')
    def _compute_variance(self):
        for rec in self:
            rec.variance = rec.closing_level - rec.expected_closing
