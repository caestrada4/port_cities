# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    _inherit = "project.project"

    @api.model
    def _compute_invoice_date_range(self):

        today = date.today()
        days_since_sunday = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(days=days_since_sunday)
        inv_start_date = self.env.user.company_id.inv_start_date or False
        return inv_start_date, last_sunday

    @api.model
    def _aggregate_timesheets(self, analytic_account_id, start_date, end_date, task_ids=None):

        if not analytic_account_id:
            return []

        params = [analytic_account_id, start_date, end_date]
        sql = """
            SELECT user_id, SUM(unit_amount) AS total_hours,
                   array_agg(id) AS line_ids
            FROM account_analytic_line
            WHERE account_id = %s
              AND invoiceable_analytic_line = 't'
              AND date >= %s
              AND date <= %s
              AND project_id IS NOT NULL
              AND project_invoice_line_id IS NULL
        """
        if task_ids:
            # safe guard: ensure task_ids is non-empty list/tuple
            t_ids = tuple(int(x) for x in task_ids) if task_ids else ()
            if not t_ids:
                return []
            sql += " AND task_id IN %s"
            params.append(t_ids)

        sql += " GROUP BY user_id ORDER BY user_id ASC"
        self.env.cr.execute(sql, tuple(params))
        rows = self.env.cr.fetchall()
        # rows: [(user_id, total_hours, [id1,id2,...]), ...]
        results = []
        for row in rows:
            user_id = row[0]
            total_hours = row[1] or 0.0
            line_ids = row[2] or []
            results.append((user_id, float(total_hours), tuple(line_ids)))
        return results

    @api.model
    def _determine_product_and_price(self, sale_order, employee, fallback_employee_data):
        """
        Returns (product_record, price_unit, uom_id)
        - sale_order: sale.order record or False
        - employee: hr.employee record or empty
        - fallback_employee_data: dict returned by action_search_employee if no hr.employee exists
        """
        # Determine product (inhouse vs outsource)
        company = self.env.user.company_id
        product = False
        uom_id = False
        price_unit = 0.0

        if employee:
            job = getattr(employee, 'job_id', False)
            if not job:
                raise UserError(_("Employee %s has no job set.") % (employee.name,))
            if employee.company_id.id == company.id:
                product = job.product_inhouse_id
            else:
                product = job.product_outsource_id
            uom_id = product.uom_id.id if product and product.uom_id else False
        else:
            # fallback structure expected from original code
            if fallback_employee_data['company_id'] == company.id:
                product = fallback_employee_data['inhouse']
            else:
                product = fallback_employee_data['outsource']
            uom_id = fallback_employee_data.get('uom_id')

        if not product:
            raise UserError(_("No product found for employee / fallback data."))

        # Determine price_unit: if sale order has pricelist and partner, compute pricelist price
        if sale_order and sale_order.pricelist_id and sale_order.partner_id:
            # Build product with context for pricelist
            try:
                product_variant = product.with_context(
                    lang=sale_order.partner_id.lang,
                    partner=sale_order.partner_id.id,
                    quantity=1,
                    date=sale_order.date_order,
                    pricelist=sale_order.pricelist_id.id,
                    uom=product.uom_id.id if product.uom_id else None,
                )
                # use the product price (tax complication omitted; adapt if needed)
                price_unit = product_variant.price
            except Exception:
                price_unit = product.list_price
        else:
            price_unit = product.list_price

        return product, price_unit, uom_id

    @api.model
    def _create_invoice_line_record(self, invoice, section_id, employee_id, product, price_unit, qty, uom_id, analytic_account_id):
        """Create a single invoice line. Returns created line record."""
        vals = {
            'layout_category_id': section_id.id if section_id else False,
            'employee_id': employee_id.id if employee_id else False,
            'product_id': product.id,
            'name': "%s: %s" % (product.name, employee_id.name if employee_id else ''),
            'quantity': qty,
            'price_unit': price_unit,
            'invoice_id': invoice.id,
            'account_id': product.property_account_income_id.id if product.property_account_income_id else False,
            'uom_id': uom_id,
            'l10n_mx_edi_sat_status': 'none',  # keep original metadata if required
            'account_analytic_id': analytic_account_id,
        }
        return self.env['account.invoice.line'].create(vals)

    def create_invoice_line(self, invoice):
        """Main entry. Iterate over projects in self and create invoice lines from timesheets."""
        self.ensure_one()  # work per single project to avoid complexity; adapt if needed
        project = self
        analytic_account = project.analytic_account_id
        if not analytic_account:
            raise UserError(_("Project %s has no analytic account.") % project.display_name)

        sale_order = self.env['sale.order'].search([('analytic_account_id', '=', analytic_account.id)], limit=1)
        start_date, end_date = self._compute_invoice_date_range()

        # If analytic sections exist, aggregate per section->task set; else global aggregation
        aggregated_groups = []
        if sale_order and sale_order.analytic_account_id and getattr(sale_order.analytic_account_id, 'section_ids', False):
            for section in sale_order.analytic_account_id.section_ids:
                okr_task = getattr(section, 'task_id', False)
                if not okr_task:
                    _logger.debug("Section %s has no task_id, skipping", section.id)
                    continue
                task_ids = self.env['project.task'].search([('parent_task_id', 'child_of', okr_task.id), ('active', '=', True)]).ids
                if not task_ids:
                    continue
                groups = self._aggregate_timesheets(analytic_account.id, start_date, end_date, task_ids=task_ids)
                # Attach the section to each result for layout_category_id
                for user_id, total_hours, line_ids in groups:
                    aggregated_groups.append({
                        'section': section,
                        'user_id': user_id,
                        'hours': total_hours,
                        'line_ids': line_ids,
                    })
        else:
            groups = self._aggregate_timesheets(analytic_account.id, start_date, end_date, task_ids=None)
            for user_id, total_hours, line_ids in groups:
                aggregated_groups.append({
                    'section': False,
                    'user_id': user_id,
                    'hours': total_hours,
                    'line_ids': line_ids,
                })

        if not aggregated_groups:
            _logger.debug("No timesheets to invoice for analytic account %s", analytic_account.id)
            return True

        # create lines
        created_lines = []
        for group in aggregated_groups:
            user_id = group['user_id']
            qty = group['hours']
            section = group['section']
            line_ids = group['line_ids']

            # get employee record if exists
            employee = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
            fallback_data = {}
            if not employee:
                # custom helper expected in original code
                fallback_data = self.action_search_employee(user_id)
                if not fallback_data:
                    raise UserError(_("Cannot find employee data for user %s") % (user_id,))
                # fallback_data must provide 'inhouse'/'outsource' product records or ids
                # ensure keys are present
                if 'inhouse' not in fallback_data or 'outsource' not in fallback_data:
                    raise UserError(_("Fallback employee data incomplete for user %s") % (user_id,))

            # Determine product and price
            product, price_unit, uom_id = self._determine_product_and_price(sale_order, employee, fallback_data)

            created = self._create_invoice_line_record(
                invoice=invoice,
                section_id=section,
                employee_id=employee,
                product=product,
                price_unit=price_unit,
                qty=qty,
                uom_id=uom_id,
                analytic_account_id=analytic_account.id,
            )
            created_lines.append(created)

            if line_ids:
                self.env['account.analytic.line'].browse(line_ids).write({'project_invoice_line_id': invoice.id})

        return created_lines
