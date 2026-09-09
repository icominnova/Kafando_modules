from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FuelExpenseCategory(models.Model):
    _name = 'fuel.expense.category'
    _description = 'Fuel Expense Category'
    _order = 'name'

    name = fields.Char(
        string='Category Name',
        required=True,
    )

    active = fields.Boolean(
        default=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            'fuel_expense_category_name_company_unique',
            'unique(name, company_id)',
            'An expense category with this name already exists for this company.',
        ),
    ]


class FuelExpense(models.Model):
    _name = 'fuel.expense'
    _description = 'Fuel Station Expense'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New'),
    )

    date = fields.Date(
        string='Expense Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    station_id = fields.Many2one(
        'fuel.station',
        string='Fuel Station',
        required=True,
        default=lambda self: self.env.user.fuel_default_station_id,
        tracking=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='station_id.company_id',
        store=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )

    shift_id = fields.Many2one(
        'fuel.shift',
        string='Shift',
        domain="[('station_id', '=', station_id)]",
        tracking=True,
        help='Optional shift related to this expense.',
    )

    category_id = fields.Many2one(
        'fuel.expense.category',
        string='Expense Category',
        required=True,
        domain="[('company_id', '=', company_id)]",
        tracking=True,
    )

    description = fields.Char(
        string='Description',
        required=True,
        tracking=True,
    )

    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id',
        tracking=True,
    )

    payment_source = fields.Selection(
        [
            ('station_cash', 'Station Cash'),
            ('mobile_money', 'Mobile Money'),
            ('bank', 'Bank'),
            ('other', 'Other'),
        ],
        string='Payment Source',
        required=True,
        default='station_cash',
        tracking=True,
    )

    user_id = fields.Many2one(
        'res.users',
        string='Recorded By',
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )

    notes = fields.Text(
        string='Notes',
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        copy=False,
        tracking=True,
    )

    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
    )

    approved_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
        copy=False,
    )

    rejected_by = fields.Many2one(
        'res.users',
        string='Rejected By',
        readonly=True,
        copy=False,
    )

    rejected_date = fields.Datetime(
        string='Rejection Date',
        readonly=True,
        copy=False,
    )

    rejection_reason = fields.Text(
        string='Rejection Reason',
        copy=False,
        tracking=True,
    )

    @api.constrains('amount')
    def _check_amount(self):
        for expense in self:
            if expense.amount <= 0:
                raise ValidationError(_(
                    "The expense amount must be greater than zero."
                ))

    @api.constrains('station_id', 'shift_id')
    def _check_shift_station(self):
        for expense in self:
            if (
                expense.shift_id
                and expense.shift_id.station_id != expense.station_id
            ):
                raise ValidationError(_(
                    "The selected shift must belong to the selected fuel station."
                ))

    @api.constrains('station_id', 'category_id')
    def _check_category_company(self):
        for expense in self:
            if (
                expense.category_id
                and expense.station_id
                and expense.category_id.company_id != expense.station_id.company_id
            ):
                raise ValidationError(_(
                    "The expense category must belong to the same company as the fuel station."
                ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fuel.expense'
                ) or _('New')

        return super().create(vals_list)

    def write(self, vals):
        protected_fields = {
            'date',
            'station_id',
            'shift_id',
            'category_id',
            'description',
            'amount',
            'payment_source',
        }

        for expense in self:
            if expense.state == 'approved':
                if protected_fields.intersection(vals):
                    raise UserError(_(
                        "An approved expense cannot be modified."
                    ))

            if (
                'state' in vals
                and vals['state'] != expense.state
                and not self.env.context.get('fuel_expense_state_change')
            ):
                raise UserError(_(
                    "Expense status must be changed using the workflow buttons."
                ))

        return super().write(vals)

    def action_submit(self):
        for expense in self:
            if expense.state != 'draft':
                raise UserError(_(
                    "Only a draft expense can be submitted."
                ))

            expense.with_context(
                fuel_expense_state_change=True
            ).write({
                'state': 'submitted',
            })

    def action_approve(self):
        if not self.env.user.has_group(
            'fuel_management.group_fuel_manager'
        ):
            raise UserError(_(
                "Only a Fuel Manager or Administrator can approve expenses."
            ))

        for expense in self:
            if expense.state != 'submitted':
                raise UserError(_(
                    "Only a submitted expense can be approved."
                ))

            expense.with_context(
                fuel_expense_state_change=True
            ).write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

    def action_reject(self):
        if not self.env.user.has_group(
            'fuel_management.group_fuel_manager'
        ):
            raise UserError(_(
                "Only a Fuel Manager or Administrator can reject expenses."
            ))

        for expense in self:
            if expense.state != 'submitted':
                raise UserError(_(
                    "Only a submitted expense can be rejected."
                ))

            if not expense.rejection_reason:
                raise UserError(_(
                    "A rejection reason is required before rejecting an expense."
                ))

            expense.with_context(
                fuel_expense_state_change=True
            ).write({
                'state': 'rejected',
                'rejected_by': self.env.user.id,
                'rejected_date': fields.Datetime.now(),
            })

    def action_cancel(self):
        for expense in self:
            if expense.state == 'approved':
                raise UserError(_(
                    "An approved expense cannot be cancelled."
                ))

            expense.with_context(
                fuel_expense_state_change=True
            ).write({
                'state': 'cancelled',
            })

    def action_reset_draft(self):
        for expense in self:
            if expense.state not in ('rejected', 'cancelled'):
                raise UserError(_(
                    "Only a rejected or cancelled expense can be reset to draft."
                ))

            expense.with_context(
                fuel_expense_state_change=True
            ).write({
                'state': 'draft',
                'rejected_by': False,
                'rejected_date': False,
                'rejection_reason': False,
            })

    def action_print_expense(self):
        self.ensure_one()

        if self.state != 'approved':
            raise UserError(_(
                "Only an approved expense can be printed."
            ))

        return self.env.ref(
            'fuel_management.action_report_fuel_expense'
        ).report_action(self)

    def unlink(self):
        for expense in self:
            if expense.state not in ('draft', 'rejected', 'cancelled'):
                raise UserError(_(
                    "Only draft, rejected or cancelled expenses can be deleted."
                ))

        return super().unlink()