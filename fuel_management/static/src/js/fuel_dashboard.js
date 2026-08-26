/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class FuelDashboard extends Component {

    static template = "fuel_management.FuelDashboard";

    setup() {

        this.orm = useService("orm");

        this.state = useState({
            stations: [],
            stationId: false,

            data: {
                today_sales_amount: 0,
                today_dispensed_qty: 0,
                open_shift_count: 0,
                today_sale_count: 0,
                tanks: [],
            },
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }


    async loadDashboard() {

        const data = await this.orm.call(
            "fuel.dashboard",
            "get_dashboard_data",
            [this.state.stationId]
        );

        this.state.data = data;

        this.state.stations = data.stations;

    }


    async onStationChange(event) {

        const value = event.target.value;

        this.state.stationId = value
            ? parseInt(value)
            : false;

        await this.loadDashboard();

    }


    getStockClass(percent) {

        if (percent > 50) {
            return "fuel-stock-good";
        }

        if (percent > 20) {
            return "fuel-stock-warning";
        }

        return "fuel-stock-danger";

    }


    formatNumber(value) {

        return new Intl.NumberFormat("fr-FR", {
            maximumFractionDigits: 2,
        }).format(value || 0);

    }

}


// -------------------------------------------------------------
// REGISTER CLIENT ACTION
// -------------------------------------------------------------

registry
    .category("actions")
    .add("fuel_management.fuel_dashboard", FuelDashboard);