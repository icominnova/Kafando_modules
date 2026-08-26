from odoo import models, fields, api, _
from odoo.exceptions import UserError

class FuelShiftDefinition(models.Model):
    _name = 'fuel.shift.definition'
    _description = 'Shift Definition'

    name = fields.Char(string='Shift Name', required=True)
    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
    active = fields.Boolean(default=True)


class FuelShift(models.Model):
    _name = 'fuel.shift'
    _description = 'Fuel Shift'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc, id desc'

    name = fields.Char(string='Shift Reference', required=True, copy=False, default='New')
    station_id = fields.Many2one('fuel.station', string='Station', required=True, tracking=True)
    shift_definition_id = fields.Many2one('fuel.shift.definition', string='Shift Type', tracking=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.today, tracking=True)
    attendant_id = fields.Many2one('hr.employee', string='Attendant', tracking=True)
    supervisor_id = fields.Many2one('res.users', string='Supervisor')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'In Progress'),
        ('validated', 'Validated'),
    ], string='Status', default='draft', tracking=True)
    notes = fields.Text(string='Notes')

    meter_reading_ids = fields.One2many('fuel.meter.reading', 'shift_id', string='Meter Readings')
    dip_reading_ids = fields.One2many('fuel.dip.reading', 'shift_id', string='Dip Readings')

    total_dispensed = fields.Float(string='Total Dispensed (L)', compute='_compute_totals', store=True)
    total_sales_amount = fields.Float(string='Total Sales', compute='_compute_totals', store=True, digits='Account')
    currency_id = fields.Many2one('res.currency', related='station_id.company_id.currency_id')

    company_id = fields.Many2one(
        'res.company',
        related='station_id.company_id',
        string='Company',
        store=True,
        index=True,
        readonly=True,
    )

    stock_posted = fields.Boolean(
        string='Stock Posted',
        default=False,
        copy=False,
        readonly=True,
        tracking=True,
    )
    
    @api.depends('meter_reading_ids.dispensed_qty', 'meter_reading_ids.total_amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_dispensed = sum(rec.meter_reading_ids.mapped('dispensed_qty'))
            rec.total_sales_amount = sum(rec.meter_reading_ids.mapped('total_amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fuel.shift') or 'New'
        return super().create(vals_list)

    def action_open(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft shifts can be opened.'))
            rec.state = 'open'


    def action_validate(self):
        self.ensure_one()

        if self.state != 'open':
            raise UserError(_('Only open shifts can be validated.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Confirm Closing Indexes'),
            'res_model': 'fuel.shift.validation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shift_id': self.id,
            },
        }
    
    def action_print_report(self):
        for rec in self:
            if rec.state != 'validated':
                raise UserError(_(
                    "Shift '%(shift)s' cannot be printed: it must be validated first "
                    "(current status: %(status)s).",
                    shift=rec.name,
                    status=dict(rec._fields['state'].selection).get(rec.state),
                ))
        return self.env.ref('fuel_management.action_report_fuel_shift').report_action(self)