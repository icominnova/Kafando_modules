from odoo import models, api, fields

class FuelPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    fuel_station_id = fields.Many2one(
        'fuel.station',
        string='Fuel Station',
        help='Fuel station receiving this purchase.'
    )
