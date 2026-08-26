from odoo import models, fields, api, _
from odoo.exceptions import UserError

class FuelPriceWizard(models.TransientModel):
    _name = 'fuel.price.wizard'
    _description = 'Fuel Price Update Wizard'

    product_id = fields.Many2one('product.product', string='Fuel Product', required=True,
        domain=[('type', '=', 'consu')])
    new_price = fields.Float(string='New Price', required=True, digits='Product Price')
    station_ids = fields.Many2many('fuel.station', string='Stations',
        help='Leave empty to update all stations')
    nozzle_count = fields.Integer(string='Nozzles to Update', compute='_compute_nozzle_count')

    @api.depends('product_id', 'station_ids')
    def _compute_nozzle_count(self):
        for rec in self:
            domain = [('product_id', '=', rec.product_id.id)] if rec.product_id else []
            if rec.station_ids:
                domain += [('station_id', 'in', rec.station_ids.ids)]
            rec.nozzle_count = self.env['fuel.nozzle'].search_count(domain)

    def action_apply(self):
        self.ensure_one()
        if not self.new_price or self.new_price <= 0:
            raise UserError(_('Please enter a valid price greater than zero.'))
        domain = [('product_id', '=', self.product_id.id)]
        if self.station_ids:
            domain += [('station_id', 'in', self.station_ids.ids)]
        nozzles = self.env['fuel.nozzle'].search(domain)
        nozzles.write({'current_price': self.new_price})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Price Updated'),
                'message': _('Price updated for %d nozzle(s) to %s.') % (len(nozzles), self.new_price),
                'type': 'success',
            }
        }
