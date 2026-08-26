from odoo import models, fields, api
from datetime import date

class FuelLicense(models.Model):
    _name = 'fuel.license'
    _description = 'Fuel Station License & Compliance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'expiry_date asc'

    name = fields.Char(string='License Name', required=True)
    station_id = fields.Many2one('fuel.station', string='Station', required=True)
    license_type = fields.Selection([
        ('operating', 'Operating License'),
        ('fire_safety', 'Fire Safety Certificate'),
        ('environmental', 'Environmental Clearance'),
        ('weights', 'Weights & Measures'),
        ('trade', 'Trade License'),
        ('other', 'Other'),
    ], string='License Type', required=True, default='operating')
    license_number = fields.Char(string='License Number')
    issuing_authority = fields.Char(string='Issuing Authority')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date', required=True, tracking=True)
    document = fields.Binary(string='Document', attachment=True)
    document_name = fields.Char(string='Document Name')
    state = fields.Selection([
        ('valid', 'Valid'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='Status', compute='_compute_state', store=True, tracking=True)
    days_to_expiry = fields.Integer(string='Days to Expiry', compute='_compute_state', store=True)
    notes = fields.Text(string='Notes')

    @api.depends('expiry_date')
    def _compute_state(self):
        today = date.today()
        for rec in self:
            if not rec.expiry_date:
                rec.state = 'valid'
                rec.days_to_expiry = 0
                continue
            delta = (rec.expiry_date - today).days
            rec.days_to_expiry = delta
            if delta < 0:
                rec.state = 'expired'
            elif delta <= 30:
                rec.state = 'expiring'
            else:
                rec.state = 'valid'
