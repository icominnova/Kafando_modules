from odoo import models, fields, api

class FuelPump(models.Model):
    _name = 'fuel.pump'
    _description = 'Fuel Pump'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char(string='Pump Name', required=True)
    code = fields.Char(string='Pump Code')
    station_id = fields.Many2one('fuel.station', string='Station', required=True, ondelete='cascade')
    state = fields.Selection([
        ('active', 'Active'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active', tracking=True)
    notes = fields.Text(string='Notes')

    nozzle_ids = fields.One2many('fuel.nozzle', 'pump_id', string='Nozzles')
    nozzle_count = fields.Integer(compute='_compute_nozzle_count', string='Nozzles')

    @api.depends('nozzle_ids')
    def _compute_nozzle_count(self):
        for rec in self:
            rec.nozzle_count = len(rec.nozzle_ids)

    def action_view_nozzles(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Nozzles',
            'res_model': 'fuel.nozzle',
            'view_mode': 'list,form',
            'domain': [('pump_id', '=', self.id)],
            'context': {'default_pump_id': self.id, 'default_station_id': self.station_id.id},
        }
