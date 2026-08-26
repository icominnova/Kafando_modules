from odoo import models, fields, api


class FuelDashboard(models.Model):
    _name = 'fuel.dashboard'
    _description = 'Fuel Dashboard'

    name = fields.Char(default='Dashboard', readonly=True)
    station_id = fields.Many2one('fuel.station', string='Station')

    today_sales_amount = fields.Float(compute='_compute_kpis', string="Today's Sales")
    today_dispensed_qty = fields.Float(compute='_compute_kpis', string="Fuel Sold (L)")
    open_shift_count = fields.Integer(compute='_compute_kpis', string='Active Shifts')
    today_sale_count = fields.Integer(compute='_compute_kpis', string='Sale Count')

    tank_ids = fields.Many2many('fuel.tank', compute='_compute_kpis', string='Tanks')

    @api.depends('name', 'station_id')
    def _compute_kpis(self):
        today = fields.Date.today()
        for rec in self:
            shift_domain = [('date', '=', today)]
            tank_domain = []
            mr_domain = [('shift_id.date', '=', today)]

            if rec.station_id:
                shift_domain.append(('station_id', '=', rec.station_id.id))
                tank_domain.append(('station_id', '=', rec.station_id.id))
                mr_domain.append(('station_id', '=', rec.station_id.id))

            shifts_today = self.env['fuel.shift'].search(shift_domain)
            rec.today_sales_amount = sum(shifts_today.mapped('total_sales_amount'))
            rec.today_dispensed_qty = sum(shifts_today.mapped('total_dispensed'))
            rec.open_shift_count = len(shifts_today.filtered(lambda s: s.state == 'open'))
            rec.today_sale_count = self.env['fuel.meter.reading'].search_count(mr_domain)
            rec.tank_ids = self.env['fuel.tank'].search(tank_domain)


    @api.model
    def get_dashboard_data(self, station_id=False):
        today = fields.Date.today()

        shift_domain = [('date', '=', today)]
        tank_domain = []
        mr_domain = [('shift_id.date', '=', today)]

        if station_id:
            shift_domain.append(('station_id', '=', station_id))
            tank_domain.append(('station_id', '=', station_id))
            mr_domain.append(('station_id', '=', station_id))


        shifts_today = self.env['fuel.shift'].search(shift_domain)
        today_sales_amount = sum(shifts_today.mapped('total_sales_amount'))
        today_dispensed_qty = sum(shifts_today.mapped('total_dispensed'))
        open_shift_count = len(shifts_today.filtered(lambda s: s.state == 'open'))


        today_sale_count = self.env['fuel.meter.reading'].search_count(mr_domain)
        tanks = self.env['fuel.tank'].search(tank_domain)
        tank_data = []

        for tank in tanks:
            tank_data.append({
                'id': tank.id,
                'name': tank.name,
                'product': tank.product_id.display_name,
                'current_stock': tank.current_stock,
                'capacity': tank.capacity,
                'stock_percent': tank.stock_percent,
                'state': tank.state,
            })

        stations = self.env['fuel.station'].search([])
        station_data = [
            {
                'id': station.id,
                'name': station.name,
            }
            for station in stations
        ]


        return {
            'today_sales_amount': today_sales_amount,
            'today_dispensed_qty': today_dispensed_qty,
            'open_shift_count': open_shift_count,
            'today_sale_count': today_sale_count,
            'tanks': tank_data,
            'stations': station_data,
            'selected_station_id': station_id or False,
        }