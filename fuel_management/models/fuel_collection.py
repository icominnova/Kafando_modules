from odoo import models, fields, api


class FuelCollection(models.Model):
    _name = 'fuel.collection'
    _description = 'Fuel Cash Collection'
    _rec_name = 'shift_id'
    _order = 'id desc'

    shift_id = fields.Many2one(
        'fuel.shift',
        string='Shift',
        required=True,
        ondelete='cascade',
    )

    station_id = fields.Many2one(
        'fuel.station',
        related='shift_id.station_id',
        string='Station',
        store=True,
        readonly=True,
    )

    company_id = fields.Many2one(
        'res.company',
        related='station_id.company_id',
        string='Company',
        store=True,
        index=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='station_id.company_id.currency_id',
        string='Currency',
        store=True,
        readonly=True,
    )

    expected_amount = fields.Monetary(
        string='Expected Sales',
        related='shift_id.total_sales_amount',
        currency_field='currency_id',
        store=True,
        readonly=True,
    )

    cash_amount = fields.Monetary(
        string='Cash',
        currency_field='currency_id',
        default=0.0,
    )

    mobile_money_amount = fields.Monetary(
        string='Mobile Money',
        currency_field='currency_id',
        default=0.0,
    )

    collected_amount = fields.Monetary(
        string='Total Collected',
        compute='_compute_collection',
        currency_field='currency_id',
        store=True,
    )

    difference = fields.Monetary(
        string='Difference',
        compute='_compute_collection',
        currency_field='currency_id',
        store=True,
    )

    notes = fields.Text(
        string='Notes',
    )

    @api.depends(
        'cash_amount',
        'mobile_money_amount',
        'expected_amount',
    )
    def _compute_collection(self):
        for rec in self:
            rec.collected_amount = (
                rec.cash_amount
                + rec.mobile_money_amount
            )

            rec.difference = (
                rec.collected_amount
                - rec.expected_amount
            )