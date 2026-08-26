from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class FuelTank(models.Model):
    _name = 'fuel.tank'
    _description = 'Fuel Tank'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char(string='Tank Name', required=True)
    station_id = fields.Many2one('fuel.station', string='Station', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Fuel Product', required=True,
        domain=[('type', '=', 'consu')])
    capacity = fields.Float(string='Tank Capacity (L)', required=True)
    current_stock = fields.Float(string='Current Stock (L)', tracking=True)
    min_stock_alert = fields.Float(string='Min. Stock Alert (L)')
    state = fields.Selection([
        ('normal', 'Normal'),
        ('low', 'Low Stock'),
        ('critical', 'Critical'),
        ('empty', 'Empty'),
    ], string='Stock Status', compute='_compute_state', store=True)
    notes = fields.Text(string='Notes')

    stock_percent = fields.Float(string='Fill %', compute='_compute_stock_percent', store=True)

    @api.depends('current_stock', 'min_stock_alert', 'capacity')
    def _compute_state(self):
        for rec in self:
            if rec.current_stock <= 0:
                rec.state = 'empty'
            elif rec.current_stock <= rec.min_stock_alert:
                rec.state = 'critical'
            elif rec.current_stock <= rec.min_stock_alert * 2:
                rec.state = 'low'
            else:
                rec.state = 'normal'

    @api.depends('current_stock', 'capacity')
    def _compute_stock_percent(self):
        for rec in self:
            rec.stock_percent = (rec.current_stock / rec.capacity * 100) if rec.capacity else 0.0
        
    def action_stock_adjustment(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Adjustment',
            'res_model': 'fuel.tank',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def _adjust_stock(self, delta):
        """Ajuste le stock de la cuve. deta>0 = Entrée, delta<0 = sortie."""
        for rec in self:
            rec.current_stock += delta

    @api.constrains('current_stock', 'capacity')
    def _check_stock_bounds(self):
        for rec in self:
            if rec.current_stock > rec.capacity:
                raise ValidationError(_(
                    "Tank '%(tank)s': current stock (%(stock).2f L) cannot exceed "
                    "its capacity (%(capacity).2f L).",
                    tank=rec.name, stock=rec.current_stock, capacity=rec.capacity,
                ))

            if rec.current_stock < 0:
                raise ValidationError(_(
                "Tank '%(tank)s': current stock cannot be negative (%(stock).2f L).",
                tank=rec.name, stock=rec.current_stock,
            ))