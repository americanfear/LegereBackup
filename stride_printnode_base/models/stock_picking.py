# Copyright 2021 VentorTech OU
# See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'printnode.mixin', 'printnode.scenario.mixin']

    def _compute_state(self):
        """Override to catch status updates
        """
        previous_states = {rec.id: rec.state for rec in self}

        super()._compute_state()

        for record in self:
            # with_company() used to print on correct printer when calling from scheduled actions
            if record.id and previous_states.get(record.id) != record.state:
                record.with_company(record.company_id).print_scenarios(
                    'print_document_on_picking_status_change')

    def _put_in_pack(self, move_line_ids, create_package_level=True):
        package = super(StockPicking, self)._put_in_pack(move_line_ids, create_package_level)

        if package:
            self.print_scenarios(action='print_package_on_put_in_pack', packages_to_print=package)

        return package

    def button_validate(self):
        """ Overriding the default method to add custom logic with print scenarios
            for picking validate.
        """
        res = super(StockPicking, self).button_validate()

        if res is True:
            printed = self.print_scenarios(action='print_document_on_transfer')

            if printed:
                self.write({'printed': True})

            # Print product labels
            self.print_scenarios(action='print_product_labels_on_transfer')

            # Print lot labels
            self.print_scenarios(action='print_single_lot_labels_on_transfer_after_validation')
            self.print_scenarios(action='print_multiple_lot_labels_on_transfer_after_validation')

            # Print packages
            self.print_scenarios(action='print_packages_label_on_transfer')

            # Print operations
            self.print_scenarios(action='print_operations_document_on_transfer')

        return res

    def direct_print_shipping_labels(self):
        """ Print last shipping label if possible.
        """
        self.ensure_one()

        if self.picking_type_code != 'outgoing':
            return
        
        user = self.env.user
        printer = user.get_shipping_label_printer(self.carrier_id, raise_exc=True)

        for shipment in self.ep_shipment_ids:
            #TODO We need to add support for other label types like png's and return labels.
            if shipment.label_url and shipment.label_url.endswith('.pdf'):
                printnode_data = {
                    'printerId': printer.printnode_id,
                    'qty': 1,
                    'title': shipment.name,
                    'contentType': 'pdf_uri',
                    'content': shipment.label_url,
                }
                printer._post_printnode_job(printnode_data)
            else:
                raise UserError(_('Currently Label Printing only works for PDF labels'))

            if self.env.company.print_package_with_label and shipment.package_id:
                report_id = self.env.company.printnode_package_report
                if not report_id:
                    raise UserError(_(
                        'There are no available package report for printing, please, '
                        'define "Package Report to Print" in Direct Print / Settings menu'
                    ))

                printer.printnode_print(report_id, shipment.package_id)       
       
        return

    def send_to_shipper(self):
        """
        Redefining a standard method
        """
        user = self.env.user
        company = self.env.company

        auto_print = company.auto_send_slp and \
            company.printnode_enabled and user.printnode_enabled

        if auto_print:
            # Simple check if shipping printer set, raise exception if no shipping printer found
            user.get_shipping_label_printer(self.carrier_id, raise_exc=True)

        super(StockPicking, self).send_to_shipper()

        if auto_print:
            self.with_context(raise_exception_slp=False).direct_print_shipping_labels()

    def _create_backorder(self):
        backorders = super(StockPicking, self)._create_backorder()

        if backorders:
            printed = self.print_scenarios(
                action='print_document_on_backorder',
                ids_list=backorders.mapped('id'))

            if printed:
                backorders.write({'printed': True})

        return backorders



    def _scenario_print_single_lot_labels_on_transfer_after_validation(
        self, scenario, number_of_copies=1, **kwargs
    ):
        """
        Print single lot label for each move line (after validation)
        Special method to provide custom logic of printing
        (like printing labels through wizards)
        """

        printed = self._scenario_print_single_lot_label_on_transfer(
            scenario=scenario,
            number_of_copies=number_of_copies,
            **kwargs
        )

        return printed

    def _scenario_print_multiple_lot_labels_on_transfer_after_validation(
        self, scenario, number_of_copies=1, **kwargs
    ):
        """
        Print multiple lot labels (depends on quantity) for each move line (after validation)
        Special method to provide custom logic of printing
        (like printing labels through wizards)
        """

        printed = self._scenario_print_multiple_lot_labels_on_transfer(
            scenario=scenario,
            number_of_copies=number_of_copies,
            **kwargs
        )

        return printed

    def _scenario_print_single_lot_label_on_transfer(
        self, scenario, report_id, printer_id, number_of_copies=1, **kwargs
    ):
        """
        Print single lot label for each move line (real time)
        Special method to provide custom logic of printing
        (like printing labels through wizards)
        """
        changed_move_lines = kwargs.get('changed_move_lines', self.move_line_ids)
        print_options = kwargs.get('options', {})

        return self._print_lot_labels_report(
            changed_move_lines,
            report_id,
            printer_id,
            with_qty=False,
            copies=number_of_copies,
            options=print_options)

    def _scenario_print_multiple_lot_labels_on_transfer(
        self, scenario, report_id, printer_id, number_of_copies=1, **kwargs
    ):
        """
        Print multiple lot labels (depends on quantity) for each move line (real time)
        Special method to provide custom logic of printing (like printing labels through wizards)
        """
        changed_move_lines = kwargs.get('changed_move_lines', self.move_line_ids)
        print_options = kwargs.get('options', {})

        return self._print_lot_labels_report(
            changed_move_lines,
            report_id,
            printer_id,
            with_qty=True,
            copies=number_of_copies,
            options=print_options)

    def _scenario_print_product_labels_on_transfer(
            self, scenario, number_of_copies=1, **kwargs
    ):
        """
        Print multiple product labels (depends on quantity) for each move line (after validation)
        Special method to provide custom logic of printing (like printing labels through wizards)
        """
        printed = self._scenario_print_multiple_product_labels_on_transfer(
            scenario=scenario,
            number_of_copies=number_of_copies,
            **kwargs
        )

        return printed

    def _scenario_print_single_product_label_on_transfer(
        self, scenario, number_of_copies=1, **kwargs
    ):
        """
        Print single product label for each move line (real time)
        Special method to provide custom logic of printing (like printing labels through wizards)
        """
        prepared_data = self._prepare_data_for_scenarios_to_print_product_labels(
            scenario,
            move_lines=kwargs.get('changed_move_lines', self.move_line_ids),
            **kwargs,
        )

        if not prepared_data:
            return False

        printed = prepared_data.get('printer_id').printnode_print(
            report_id=prepared_data.get('report_id'),
            objects=prepared_data.get('product_ids'),
            data=prepared_data.get('data'),
            copies=number_of_copies,
            options=prepared_data.get('print_options', {}),
        )

        return printed

    def _scenario_print_multiple_product_labels_on_transfer(
        self, scenario, number_of_copies=1, **kwargs
    ):
        """
        Print multiple product labels for each move line (real time)
        Special method to provide custom logic of printing (like printing labels through wizards)
        """
        prepared_data = self._prepare_data_for_scenarios_to_print_product_labels(
            scenario,
            move_lines=kwargs.get('changed_move_lines', self.move_line_ids),
            with_qty=True,
            **kwargs,
        )

        if not prepared_data:
            return False

        printed = prepared_data.get('printer_id').printnode_print(
            report_id=prepared_data.get('report_id'),
            objects=prepared_data.get('product_ids'),
            data=prepared_data.get('data'),
            copies=number_of_copies,
            options=prepared_data.get('print_options', {}),
        )

        return printed

    def _scenario_print_packages_label_on_transfer(
        self, report_id, printer_id, number_of_copies=1, **kwargs
    ):
        packages = self.mapped('package_ids')
        print_options = kwargs.get('options', {})
        printer_id.printnode_print(
            report_id,
            packages,
            copies=number_of_copies,
            options=print_options,
        )

    def _scenario_print_document_on_picking_status_change(
        self, report_id, printer_id, number_of_copies=1, **kwargs
    ):
        print_options = kwargs.get('options', {})

        printed = printer_id.printnode_print(
            report_id,
            self,
            copies=number_of_copies,
            options=print_options,
        )
        return printed

    def _scenario_print_package_on_put_in_pack(
        self, report_id, printer_id, number_of_copies, packages_to_print, **kwargs
    ):
        """
        Print new packages from stock.picking.

        packages_to_print is a recordset of stock.quant.package to print
        """
        print_options = kwargs.get('options', {})

        printer_id.printnode_print(
            report_id,
            packages_to_print,
            copies=number_of_copies,
            options=print_options,
        )

    def _scenario_print_operations_document_on_transfer(
        self, report_id, printer_id, number_of_copies=1, **kwargs
    ):
        """
        Print reports from the invoice document on transfer scenario.
        """
        wizard = self.env['printnode.print.stock.move.reports.wizard'].with_context(
            active_id=self.id,
            active_model='stock.picking',
        ).create({
            'report_id': report_id.id,
            'printer_id': printer_id.id,
            'number_copy': number_of_copies,
        })
        wizard.do_print()

    def _change_number_of_lot_labels_to_one(self, custom_barcodes):
        """
        This method changes barcodes quantities to 1.
        Example of incoming data:
            defaultdict(<class 'list'>, {36: [('0002', 3), ('0003', 6)]})

        Return data example:
            defaultdict(<class 'list'>, {36: [('0002', 1), ('0003', 1)]})
        """
        new_custom_barcodes = defaultdict(list)
        for key, val in custom_barcodes.items():
            for code, qty in val:
                new_custom_barcodes[key].append((code, 1))

        return new_custom_barcodes

    def _get_product_lines_from_stock_move_lines(self, move_lines, **kwargs):
        """
        This method returns product_lines with product_id and quantity from stock_move_lines.
        """
        product_lines = []
        unit_uom = self.env.ref('uom.product_uom_unit')

        move_lines_qty_done = move_lines.filtered(lambda ml: ml.qty_done > 0)
        for move_line in move_lines_qty_done:
            quantity_done = 1
            if move_line.product_uom_id == unit_uom:
                quantity_done = move_line.qty_done

            product_lines.append((0, 0, {
                'product_id': move_line.product_id.id,
                'quantity': quantity_done,
            }))

        return product_lines

    def _print_lot_labels_report(
        self, changed_move_lines, report_id, printer_id,
        with_qty=False, copies=1, options=None
    ):
        """
        This method runs printing of lots labels. It can print single lot label for each lot or
        quantity based on qty_done attribute
        """
        move_lines_with_lots_and_qty_done = changed_move_lines.filtered(
            lambda ml: ml.lot_id and not ml.printnode_printed and ml.qty_done > 0)

        printed = False

        for move_line in move_lines_with_lots_and_qty_done:
            lots = self.env['stock.lot']

            if with_qty:
                for i in range(int(move_line.qty_done)):
                    lots = lots.concat(move_line.lot_id)
            else:
                lots = lots.concat(move_line.lot_id)

            if lots:
                printer_id.printnode_print(
                    report_id,
                    lots,
                    copies=copies,
                    options=options,
                )

                move_line.write({'printnode_printed': True})
                printed = True

        return printed

    def _prepare_data_for_scenarios_to_print_product_labels(
        self, scenario, move_lines=None, with_qty=False, **kwargs,
    ):
        """
        This method prepares data to print product labels (using Stride Print Labels wizard)

        :param scenario: required current scenario
        :param moves: required stock moves from stock picking
        :param with_qty: optional boolean to change the picking_quantity mode of wizard
        """
        product_lines = self._get_product_lines_from_stock_move_lines(move_lines=move_lines)

        move_lines_with_qty_done = move_lines.filtered(lambda ml: ml.qty_done > 0)

        product_ids = move_lines_with_qty_done.mapped('product_id')

        if not product_ids:
            # Print nothing when no move lines where product with quantity_done > 0
            return False

        # In Odoo 16 there is a wizard to print labels, so we have to use it to avoid overriding
        # a lot of logic related to label format selection / printer selection / etc.
        wizard = self._init_product_label_layout_wizard(
            active_model='product.product',
            picking_quantity='custom_per_product' if with_qty else 'custom',
            product_ids=product_ids,
            product_line_ids=product_lines,
            print_format=self.env.company.print_labels_format,
        )

        printing_data = self._prepare_printing_data(scenario, wizard, **kwargs)
        printing_data['product_ids'] = product_ids

        return printing_data

    def _init_product_label_layout_wizard(
        self, active_model, picking_quantity, product_ids, product_line_ids, print_format, **kwargs
    ):
        """
        This method needed for ZPL Label Designer to allow pass additional fields to wizard.
        For now we use it to pass zld_label_id field to wizard.
        """
        try:
            return self.env['product.label.layout'].create({
                'active_model': active_model,
                'picking_quantity': picking_quantity,
                'product_ids': product_ids,
                'product_line_ids': product_line_ids,
                'print_format': print_format,
                **kwargs,  # Allow to pass any custom fields to wizard
            })
        except ValueError:
            raise UserError(
                _(
                    "One or more wrong fields for product.label.layout model passed: %s",
                    ', '.join(kwargs.keys())
                )
            )

    def _prepare_printing_data(self, scenario, wizard, **kwargs):
        """
        This method prepares all data required for scenarios to print something using Print Labels
        wizard (wizard parameter)
        """
        print_options = kwargs.get('options', {})

        # Printer from scenario should be used if it is set, otherwise use the default printer
        # from 'product.label.layout' wizard
        if scenario.printer_id:
            printer_id = scenario.printer_id
        else:
            # Manually call default method for printer_id to update printer based on
            # other wizard fields values
            printer_id, printer_bin = wizard._get_default_printer()
            # We also should replace printer bin to the value
            if printer_bin:
                print_options['bin'] = printer_bin.name

        # Get report
        xml_id, data = wizard._prepare_report_data()
        report_id = self.env.ref(xml_id)

        # Change type of dictionary keys to string
        if data['quantity_by_product']:
            data['quantity_by_product'] = self.change_dictionary_keys_type_to_string(
                data['quantity_by_product'])

        return {
            'printer_id': printer_id,
            'report_id': report_id,
            'data': data,
            'print_options': print_options,
        }

    def open_print_operation_reports_wizard(self):
        """ Returns action window with 'Print Operation Reports Wizard'
        """
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Print Operation Reports Wizard'),
            'res_model': 'printnode.print.stock.move.reports.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'stride_printnode_base.printnode_print_stock_move_reports_wizard_form').id,
            'target': 'new',
            'context': self.env.context,
        }
