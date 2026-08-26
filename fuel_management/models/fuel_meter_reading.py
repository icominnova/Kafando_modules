from odoo import models, fields, api

class FuelMeterReading(models.Model):
    _name = 'fuel.meter.reading'
    _description = 'Fuel Meter Reading'
    _rec_name = 'nozzle_id'

    shift_id = fields.Many2one('fuel.shift', string='Shift', required=True, ondelete='cascade')
    station_id = fields.Many2one('fuel.station', related='shift_id.station_id', store=True)
    nozzle_id = fields.Many2one('fuel.nozzle', string='Nozzle', required=True,
        domain="[('station_id', '=', station_id)]")
    pump_id = fields.Many2one('fuel.pump', related='nozzle_id.pump_id', store=True, string='Pump')
    product_id = fields.Many2one('product.product', related='nozzle_id.product_id', store=True, string='Product')

    opening_reading = fields.Float(string='Opening Reading (L)', digits=(16, 3))
    closing_reading = fields.Float(string='Closing Reading (L)', digits=(16, 3))
    dispensed_qty = fields.Float(string='Dispensed (L)', compute='_compute_dispensed', store=True, digits=(16, 3))
    unit_price = fields.Float(string='Unit Price', digits='Product Price')
    total_amount = fields.Float(string='Total Amount', compute='_compute_total', store=True, digits='Account')
    notes = fields.Text(string='Notes')

    @api.depends('opening_reading', 'closing_reading')
    def _compute_dispensed(self):
        for rec in self:
            rec.dispensed_qty = max(0.0, rec.closing_reading - rec.opening_reading)

    @api.depends('dispensed_qty', 'unit_price')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = rec.dispensed_qty * rec.unit_price

    @api.onchange('nozzle_id')
    def _onchange_nozzle(self):
        if self.nozzle_id:
            self.unit_price = self.nozzle_id.current_price

    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.nozzle_id.tank_id:
                rec.nozzle_id.tank_id._adjust_stock(-rec.dispensed_qty)
        return records

    def write(self, vals):
        old_data = {rec.id: (rec.dispensed_qty, rec.nozzle_id.tank_id) for rec in self}
        res = super().write(vals)
        for rec in self:
            old_qty, old_tank = old_data[rec.id]
            new_qty, new_tank = rec.dispensed_qty, rec.nozzle_id.tank_id
            if old_tank:
                old_tank._adjust_stock(old_qty)

            if new_tank:
                new_tank._adjust_stock(-new_qty)
        return res

    def unlink(self):
        for rec in self:
            if rec.nozzle_id.tank_id:
                rec.nozzle_id.tank_id._adjust_stock(rec.dispensed_qty)
        return super().unlink()