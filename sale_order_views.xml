<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <template id="report_invoice_document" inherit_id="account.report_invoice_document">
        <!-- Columna Cajas en cabecera -->
        <xpath expr="//th[@name='th_quantity']" position="after">
            <th name="th_boxes" class="text-end">Cajas</th>
        </xpath>
        <!-- Columna Cajas por línea -->
        <xpath expr="//td[@name='td_quantity']" position="after">
            <td name="td_boxes" class="text-end">
                <span t-field="line.virtual_box" />
            </td>
        </xpath>
        <!-- Fila de totales debajo de la última línea, alineada con las columnas -->
        <xpath expr="//td[@name='td_quantity']" position="attributes">
            <attribute name="t-att-style">
                <![CDATA['' if not line_last else 'border-bottom: 2px solid #dee2e6;']]>
            </attribute>
        </xpath>
        <xpath expr="//div[@id='right-elements']" position="before">
            <div class="row mb-2">
                <div class="col-12">
                    <table class="table table-sm mb-0" style="border-top: 2px solid #dee2e6;">
                        <tbody>
                            <tr>
                                <td style="width:50%;"></td>
                                <td class="text-end fw-bold" style="width:15%;">
                                    <span t-field="o.total_quantity"/>
                                </td>
                                <td class="text-end fw-bold" style="width:10%;">
                                    <span t-field="o.total_virtual_box"/>
                                </td>
                                <td style="width:25%;"></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </xpath>
    </template>

</odoo>
