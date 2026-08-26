from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FuelTankReplenishment(models.TransientModel):
    _name = 'fuel.tank.replenishment'
    _description = 'Tank Replenishment'

    tank_id = fields.Many2one('fuel.tank', string='Tank', required=True)
    station_id = fields.Many2one(related='tank_id.station_id', string='Station')
    shift_id = fields.Many2one('fuel.shift', string='Shift', required=True,
        domain="[('station_id', '=', station_id)]")
    quantity = fields.Float(string='Quantity Received (L)', required=True)

    def action_confirm(self):
        self.ensure_one()
        if self.quantity <= 0:
            raise UserError(_('The received quantity must be positive.'))

        dip_reading = self.env['fuel.dip.reading'].search([
            ('tank_id', '=', self.tank_id.id),
            ('shift_id', '=', self.shift_id.id),
        ], limit=1)

        if not dip_reading:
            raise UserError(_(
                "Cannot replenish: no dip reading (jaugeage) found for tank "
                "'%(tank)s' on shift '%(shift)s'. Please record the dip reading first.",
                tank=self.tank_id.name, shift=self.shift_id.name,
            ))

        self.tank_id._adjust_stock(self.quantity)
        dip_reading.received_qty += self.quantity

        return {'type': 'ir.actions.act_window_close'}