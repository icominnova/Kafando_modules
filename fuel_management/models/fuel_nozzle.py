from odoo import models, fields, api

class FuelNozzle(models.Model):
    _name = 'fuel.nozzle'
    _description = 'Fuel Nozzle'
    _rec_name = 'name'

    name = fields.Char(string='Nozzle Name', required=True)
    pump_id = fields.Many2one('fuel.pump', string='Pump', required=True, ondelete='cascade')
    station_id = fields.Many2one('fuel.station', string='Station', related='pump_id.station_id', store=True)
    product_id = fields.Many2one('product.product', string='Fuel Product', required=True,
        domain=[('type', '=', 'consu')])
    current_price = fields.Float(string='Current Price', digits='Product Price')
    state = fields.Selection([
        ('active', 'Active'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active')
    notes = fields.Text(string='Notes')

    tank_id = fields.Many2one('fuel.tank', string='Source tank',
        domain="[('station_id', '=', station_id), ('product_id', '=', product_id)]",
        help='Tank this nozzle draws fuel from. Used to automatically decrease stock on dispensing.')

    company_id = fields.Many2one(
        'res.company',
        related='station_id.company_id',
        string='Company',
        store=True,
        index=True,
        readonly=True,
    )