from odoo import models, fields, _
from odoo.exceptions import UserError


class FuelShiftValidationWizard(models.TransientModel):
    _name = 'fuel.shift.validation.wizard'
    _description = 'Shift Validation Confirmation'

    shift_id = fields.Many2one(
        'fuel.shift',
        string='Shift',
        required=True,
        readonly=True,
    )

    def action_confirm(self):
        self.ensure_one()

        shift = self.shift_id

        # Vérification du statut du shift
        if shift.state != 'open':
            raise UserError(_(
                "Only an open shift can be validated."
            ))

        if shift.stock_posted:
            raise UserError(_(
                "Stock movements for this shift "
                "have already been posted."
            ))

        #Vérifier qu'il existe des pistolets
        nozzles = self.env['fuel.nozzle'].search([
            ('station_id', '=', shift.station_id.id),
        ])

        if not nozzles:
            raise UserError(_(
                "No nozzle is configured for station '%s'."
            ) % shift.station_id.display_name)

        # 3. Vérifier les relevés compteurs
        readings = shift.meter_reading_ids
        if not readings:
            raise UserError(_(
                "No meter readings have been recorded "
                "for this shift."
            ))
        
        # 4. Empêcher deux relevés du même pistolet
        seen_nozzles = set()
        for reading in readings:
            if reading.nozzle_id.id in seen_nozzles:
                raise UserError(_(
                    "Nozzle '%s' has more than one meter "
                    "reading for this shift."
                ) % reading.nozzle_id.display_name)
            seen_nozzles.add(reading.nozzle_id.id)

        # 5. Vérifier que chaque pistolet a son relevé
        reading_nozzle_ids = set(
            readings.mapped('nozzle_id').ids
        )

        missing_nozzles = nozzles.filtered(
            lambda nozzle:
                nozzle.id not in reading_nozzle_ids
        )

        if missing_nozzles:
            names = ', '.join(
                missing_nozzles.mapped('display_name')
            )
            raise UserError(_(
                "The shift cannot be closed because "
                "the following nozzles have no meter reading:\n\n%s"
            ) % names)

        #Vérifier chaque index de clôture
        for reading in readings:
            if reading.closing_reading < reading.opening_reading:
                raise UserError(_(
                    "Invalid closing index for nozzle '%(nozzle)s'.\n\n"
                    "Opening index: %(opening).3f L\n"
                    "Closing index: %(closing).3f L",
                    nozzle=reading.nozzle_id.display_name,
                    opening=reading.opening_reading,
                    closing=reading.closing_reading,
                ))
            if not reading.tank_id:
                raise UserError(_(
                    "No tank is configured for nozzle '%s'."
                ) % reading.nozzle_id.display_name)
            
        #Regrouper les ventes par cuve
        tank_totals = {}
        for reading in readings:
            tank_id = reading.tank_id.id
            tank_totals[tank_id] = (
                tank_totals.get(tank_id, 0.0)
                + reading.dispensed_qty
            )

        #Vérifier le stock AVANT toute modification
        for tank_id, qty in tank_totals.items():
            tank = self.env['fuel.tank'].browse(tank_id)
            if qty > tank.current_stock:
                raise UserError(_(
                    "Insufficient stock in tank '%(tank)s'.\n\n"
                    "Current stock: %(stock).3f L\n"
                    "Dispensed during shift: %(qty).3f L\n"
                    "Missing: %(missing).3f L",
                    tank=tank.display_name,
                    stock=tank.current_stock,
                    qty=qty,
                    missing=qty - tank.current_stock,
                ))

        #Appliquer les sorties de stock
        for tank_id, qty in tank_totals.items():
            if qty <= 0:
                continue
            tank = self.env['fuel.tank'].browse(tank_id)
            tank._adjust_stock(-qty)
        shift.write({
            'stock_posted': True,
            'state': 'validated',
        })

        #Traçabilité
        shift.message_post(
            body=_(
                "Shift validated. "
                "Fuel stock movements have been posted "
                "based on the closing meter readings."
            )
        )
        return {
            'type': 'ir.actions.act_window_close'
        }