from odoo import models, fields


class FuelMeterCorrection(models.Model):
    _name = 'fuel.meter.correction'
    _description = 'Meter Reading Correction'
    _order = 'correction_date desc, id desc'

    reading_id = fields.Many2one(
        'fuel.meter.reading',
        string='Meter Reading',
        required=True,
        ondelete='restrict',
    )

    shift_id = fields.Many2one(
        'fuel.shift',
        related='reading_id.shift_id',
        string='Shift',
        store=True,
        readonly=True,
    )

    station_id = fields.Many2one(
        'fuel.station',
        related='reading_id.station_id',
        string='Station',
        store=True,
        readonly=True,
    )

    nozzle_id = fields.Many2one(
        'fuel.nozzle',
        related='reading_id.nozzle_id',
        string='Nozzle',
        store=True,
        readonly=True,
    )

    tank_id = fields.Many2one(
        'fuel.tank',
        related='reading_id.tank_id',
        string='Tank',
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        'res.company',
        related='reading_id.company_id',
        string='Company',
        store=True,
        readonly=True,
    )

    old_closing_reading = fields.Float(
        string='Old Closing Index',
        digits=(16, 3),
        readonly=True,
    )

    new_closing_reading = fields.Float(
        string='New Closing Index',
        digits=(16, 3),
        readonly=True,
    )

    old_dispensed_qty = fields.Float(
        string='Old Dispensed Quantity',
        digits=(16, 3),
        readonly=True,
    )

    new_dispensed_qty = fields.Float(
        string='New Dispensed Quantity',
        digits=(16, 3),
        readonly=True,
    )

    stock_adjustment_qty = fields.Float(
        string='Stock Adjustment',
        digits=(16, 3),
        readonly=True,
    )

    old_total_amount = fields.Float(
        string='Old Sales Amount',
        readonly=True,
    )

    new_total_amount = fields.Float(
        string='New Sales Amount',
        readonly=True,
    )

    reason = fields.Text(
        string='Correction Reason',
        required=True,
        readonly=True,
    )

    corrected_by = fields.Many2one(
        'res.users',
        string='Corrected By',
        default=lambda self: self.env.user,
        readonly=True,
    )

    correction_date = fields.Datetime(
        string='Correction Date',
        default=fields.Datetime.now,
        readonly=True,
    )