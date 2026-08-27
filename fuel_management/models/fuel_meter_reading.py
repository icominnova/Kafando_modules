from odoo import models, fields, api, _
from odoo.exceptions import UserError

class FuelMeterReading(models.Model):
    _name = 'fuel.meter.reading'
    _description = 'Fuel Meter Reading'
    _rec_name = 'nozzle_id'

    shift_id = fields.Many2one('fuel.shift', string='Shift', required=True, ondelete='cascade')
    shift_date = fields.Date(related='shift_id.date', store=True, index=True)
    station_id = fields.Many2one('fuel.station', related='shift_id.station_id', store=True)

    nozzle_id = fields.Many2one(
        'fuel.nozzle',
        string='Nozzle',
        required=True,
        domain="[('id', 'in', allowed_nozzle_ids)]"
    )
    
    pump_id = fields.Many2one('fuel.pump', related='nozzle_id.pump_id', store=True, string='Pump')
    tank_id = fields.Many2one('fuel.tank', related='nozzle_id.tank_id', store=True, index=True, string='Tank')
    product_id = fields.Many2one('product.product', related='nozzle_id.product_id', store=True, string='Product')

    opening_reading = fields.Float(string='Opening Reading (L)', digits=(16, 3), readonly=True)
    closing_reading = fields.Float(string='Closing Reading (L)', digits=(16, 3))
    dispensed_qty = fields.Float(string='Dispensed (L)', compute='_compute_dispensed', store=True, digits=(16, 3))
    unit_price = fields.Float(string='Unit Price', digits='Product Price')
    total_amount = fields.Float(string='Total Amount', compute='_compute_total', store=True, digits='Account')
    notes = fields.Text(string='Notes')

    company_id = fields.Many2one(
        'res.company',
        related='station_id.company_id',
        string='Company',
        store=True,
        index=True,
        readonly=True,
    )

    closing_recorded = fields.Boolean(
        string='Closing Index Recorded',
        default=False,
        copy=False,
        readonly=True,
    )

    allowed_nozzle_ids = fields.Many2many(
        'fuel.nozzle',
        related='shift_id.nozzle_ids',
        string='Allowed Nozzles',
        readonly=True,
    )
    
    def _get_previous_reading(self):
        self.ensure_one()

        if not self.nozzle_id or not self.shift_id:
            return self.env['fuel.meter.reading']

        previous_reading = self.search([
            ('nozzle_id', '=', self.nozzle_id.id),
            ('station_id', '=', self.shift_id.station_id.id),
            ('shift_date', '<=', self.shift_id.date),
            ('shift_id', '!=', self.shift_id.id),
            ('shift_id.state', '=', 'validated'),
        ], order='shift_date desc, id desc', limit=1)

        return previous_reading

    @api.depends('opening_reading', 'closing_reading')
    def _compute_dispensed(self):
        for rec in self:
            rec.dispensed_qty = max(0.0, rec.closing_reading - rec.opening_reading)

    @api.depends('dispensed_qty', 'unit_price')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = rec.dispensed_qty * rec.unit_price

    @api.onchange('nozzle_id')
    def _onchange_nozzle(self):
        if self.nozzle_id:
            self.unit_price = self.nozzle_id.current_price

            previous_reading = self._get_previous_reading()

            if previous_reading:
                self.opening_reading = previous_reading.closing_reading
            else:
                self.opening_reading = 0.0
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            nozzle_id = vals.get('nozzle_id')
            shift_id = vals.get('shift_id')

            if nozzle_id and shift_id:
                nozzle = self.env['fuel.nozzle'].browse(nozzle_id)
                shift = self.env['fuel.shift'].browse(shift_id)

                if nozzle not in shift.nozzle_ids:
                    raise UserError(_(
                        "Nozzle '%(nozzle)s' is not assigned to shift '%(shift)s'.",
                        nozzle=nozzle.display_name,
                        shift=shift.display_name,
                 ))
                
                previous_reading = self.search([
                    ('nozzle_id', '=', nozzle.id),
                    ('shift_id.station_id', '=', shift.station_id.id),
                    ('shift_id.date', '<=', shift.date),
                    ('shift_id', '!=', shift.id),
                    ('shift_id.state', '=', 'validated'),
                ], order='shift_date desc, id desc', limit=1)
                
                vals['opening_reading'] = (
                    previous_reading.closing_reading
                    if previous_reading
                    else 0.0
                )
        records = super().create(vals_list)
        return records

    def write(self, vals):
        for rec in self:

            # Interdire toute modification après validation
            if rec.shift_id.state == 'validated':
                raise UserError(_(
                    'You cannot modify a meter reading from a validated shift.'
                ))

            # Interdire la modification manuelle de l'index d'ouverture
            if (
                'opening_reading' in vals
                and vals['opening_reading'] != rec.opening_reading
            ):
                raise UserError(_(
                    'The opening reading cannot be modified. '
                    'It is automatically determined from the previous validated shift.'
                ))

            # Déterminer le shift qui sera utilisé après modification
            new_shift = self.env['fuel.shift'].browse(
                vals.get('shift_id', rec.shift_id.id)
            )

            # Déterminer le pistolet qui sera utilisé après modification
            new_nozzle = self.env['fuel.nozzle'].browse(
                vals.get('nozzle_id', rec.nozzle_id.id)
            )

            # Le pistolet doit appartenir aux pistolets déclarés du shift
            if new_nozzle not in new_shift.nozzle_ids:
                raise UserError(_(
                    "Nozzle '%(nozzle)s' is not assigned "
                    "to shift '%(shift)s'.",
                    nozzle=new_nozzle.display_name,
                    shift=new_shift.display_name,
                ))

        if 'closing_reading' in vals:
            vals['closing_recorded'] = True

        return super().write(vals)

    def unlink(self):
        return super().unlink()
    
    