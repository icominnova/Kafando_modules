import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class StockPercentWidget extends Component {
    static template = "fuel_management.StockPercentWidget";
    static props = standardFieldProps;

    get percentage() {
        return Math.round(this.props.record.data.stock_percent || 0);
    }
}

registry.category("fields").add("stock_percent_bar", {
    component: StockPercentWidget,
    supportedTypes: ["float"],
});