from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

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
        domain=lambda self: self._get_available_shift_domain(),
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

    @api.model
    def _get_available_shift_domain(self):
        today = fields.Date.context_today(self)

        collected_shift_ids = self.search([
            ('shift_id', '!=', False),
        ]).mapped('shift_id').ids

        return [
            ('date', '=', today),
            ('state', '=', 'validated'),
            ('id', 'not in', collected_shift_ids),
        ]

    @api.depends('cash_amount', 'mobile_money_amount', 'expected_amount')
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

    @api.constrains('shift_id')
    def _check_shift_collection(self):
        today = fields.Date.context_today(self)

        for rec in self:
            if not rec.shift_id:
                continue

            # Le shift doit être celui du jour
            if rec.shift_id.date != today:
                raise ValidationError(
                    _("Only today's shifts can be collected.")
                )

            # Le shift doit être validé
            if rec.shift_id.state != 'validated':
                raise ValidationError(
                    _("Only validated shifts can be collected.")
                )

            # Un shift ne peut être collecté qu'une seule fois
            duplicate = self.search_count([
                ('shift_id', '=', rec.shift_id.id),
                ('id', '!=', rec.id),
            ])

            if duplicate:
                raise ValidationError(
                    _("This shift has already been collected.")
                )