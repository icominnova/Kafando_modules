from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class FuelPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    fuel_station_id = fields.Many2one(
        'fuel.station',
        string='Fuel Station',
        help='Fuel station receiving this purchase.'
    )

    purchase_type = fields.Selection(
        [
            ('general', 'General Purchase'),
            ('fuel', 'Fuel Purchase'),
        ],
        string='Purchase Type',
        default='general',
        required=True,
        tracking=True,
    )

    @api.constrains('purchase_type', 'fuel_station_id')
    def _check_fuel_station(self):
        for order in self:
            if order.purchase_type == 'fuel' and not order.fuel_station_id:
                raise ValidationError(_(
                    "A fuel station is required for a fuel purchase."
                ))

    @api.onchange('purchase_type')
    def _onchange_purchase_type(self):
        if self.purchase_type != 'fuel':
            self.fuel_station_id = False