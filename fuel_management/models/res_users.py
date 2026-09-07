from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    fuel_station_ids = fields.Many2many(
        'fuel.station',
        'fuel_station_user_rel',
        'user_id',
        'station_id',
        string='Allowed Fuel Stations',
        help='Fuel stations this user is allowed to access.',
    )

    fuel_default_station_id = fields.Many2one(
        'fuel.station',
        string='Default Fuel Station',
        domain="[('id', 'in', fuel_station_ids)]",
        help='Station selected by default when this user creates fuel operations.',
    )

    @api.constrains('fuel_station_ids', 'fuel_default_station_id')
    def _check_default_fuel_station(self):
        for user in self:
            if (
                user.fuel_default_station_id
                and user.fuel_default_station_id not in user.fuel_station_ids
            ):
                raise ValidationError(_(
                    "The default fuel station must be one of the user's "
                    "allowed fuel stations."
                ))