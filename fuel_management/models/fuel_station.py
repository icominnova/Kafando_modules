from odoo import models, fields, api

class FuelStation(models.Model):
    _name = 'fuel.station'
    _description = 'Fuel Station'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Station Name', required=True, tracking=True)
    code = fields.Char(string='Station Code', required=True, copy=False, tracking=True)
    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    manager_id = fields.Many2one('res.users', string='Station Manager', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('active', 'Active'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active', tracking=True)
    notes = fields.Text(string='Notes')

    pump_ids = fields.One2many('fuel.pump', 'station_id', string='Pumps')
    tank_ids = fields.One2many('fuel.tank', 'station_id', string='Tanks')
    license_ids = fields.One2many('fuel.license', 'station_id', string='Licenses')

    pump_count = fields.Integer(compute='_compute_counts', string='Pumps')
    tank_count = fields.Integer(compute='_compute_counts', string='Tanks')
    license_count = fields.Integer(compute='_compute_counts', string='Licenses')

    open_shift_count = fields.Integer(compute='_compute_today_activity', string='Open Shifts')
    pending_validation_count = fields.Integer(compute='_compute_today_activity', string='Pending Validation')
    today_sales_amount = fields.Float(compute='_compute_today_activity', string="Today's Sales")
    today_dispensed_qty = fields.Float(compute='_compute_today_activity', string="Today's Volume (L)")
    today_sale_count = fields.Integer(compute='_compute_today_activity', string="Today's Sale Count")

    @api.depends('pump_ids', 'tank_ids', 'license_ids')
    def _compute_counts(self):
        for rec in self:
            rec.pump_count = len(rec.pump_ids)
            rec.tank_count = len(rec.tank_ids)
            rec.license_count = len(rec.license_ids)

    @api.depends('name')
    def _compute_today_activity(self):
        today = fields.Date.today()
        for rec in self:
            shifts_today = self.env['fuel.shift'].search([
                ('station_id', '=', rec.id),
                ('date', '=', today),
            ])
            rec.open_shift_count = len(shifts_today.filtered(lambda s: s.state == 'open'))
            rec.pending_validation_count = len(shifts_today.filtered(lambda s: s.state == 'closed'))
            rec.today_sales_amount = sum(shifts_today.mapped('total_sales_amount'))
            rec.today_dispensed_qty = sum(shifts_today.mapped('total_dispensed'))
            rec.today_sale_count = self.env['fuel.meter.reading'].search_count([
                ('station_id', '=', rec.id),
                ('shift_id.date', '=', today),
            ])

    def action_view_pumps(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pumps',
            'res_model': 'fuel.pump',
            'view_mode': 'list,form',
            'domain': [('station_id', '=', self.id)],
            'context': {'default_station_id': self.id},
        }

    def action_view_tanks(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tanks',
            'res_model': 'fuel.tank',
            'view_mode': 'list,form',
            'domain': [('station_id', '=', self.id)],
            'context': {'default_station_id': self.id},
        }

    def action_view_licenses(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Licenses',
            'res_model': 'fuel.license',
            'view_mode': 'list,form',
            'domain': [('station_id', '=', self.id)],
            'context': {'default_station_id': self.id},
        }
