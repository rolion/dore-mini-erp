"""Presentación de los resultados de Reporting: importes como cadena de 2 decimales, ids como cadena."""
from decimal import Decimal

from modules.reporting.application import queries
from modules.reporting.domain.period import Period


def money(value: Decimal | None) -> str | None:
    return None if value is None else f'{value:.2f}'


def _id(value) -> str | None:
    return None if value is None else str(value)


def period_data(period: Period) -> dict:
    return {'kind': period.kind.value, 'date_from': period.date_from.isoformat(),
            'date_to': period.date_to.isoformat()}


def dashboard_data(summary: queries.DashboardSummary) -> dict:
    return {
        'period': period_data(summary.period),
        'sales_total': money(summary.sales_total),
        'orders_count': summary.orders_count,
        'average_ticket': money(summary.average_ticket),
        'expenses_total': money(summary.expenses_total),
        'estimated_profit': money(summary.estimated_profit),
        'pending_delivery_count': summary.pending_delivery_count,
        'pending_collection_count': summary.pending_collection_count,
        'pending_collection_balance': money(summary.pending_collection_balance),
        'sales_criteria': summary.sales_criteria,
    }


def sales_data(report: queries.SalesReport) -> dict:
    return {
        'period': period_data(report.period),
        'total': money(report.total),
        'orders_count': report.orders_count,
        'average_ticket': money(report.average_ticket),
        'criteria': report.criteria,
    }


def expenses_data(report: queries.ExpensesReport) -> dict:
    return {
        'period': period_data(report.period),
        'total': money(report.total),
        'categories': [{'category_id': _id(c.category_id), 'name': c.name, 'active': c.active,
                        'total': money(c.total)} for c in report.categories],
    }


def channels_data(report: queries.ChannelReport) -> dict:
    return {
        'period': period_data(report.period),
        'channels': [{'sales_channel': c.sales_channel, 'orders_count': c.orders_count, 'total': money(c.total)}
                     for c in report.channels],
    }


def products_data(report: queries.ProductsReport) -> dict:
    return {
        'period': period_data(report.period),
        'limit': report.limit,
        'products': [{'product_id': _id(p.product_id), 'product_name': p.product_name, 'units': p.units,
                      'amount': money(p.amount)} for p in report.products],
    }


def customers_data(report: queries.CustomersReport) -> dict:
    return {
        'period': period_data(report.period),
        'limit': report.limit,
        'customers': [{'customer_id': _id(c.customer_id), 'name': c.name, 'orders_count': c.orders_count,
                       'total': money(c.total)} for c in report.customers],
    }


def _customer(row: queries.PendingRow) -> dict | None:
    if row.order.customer_id is None:
        return None
    return {'id': _id(row.order.customer_id), 'name': row.customer_name}


def _pending_row(row: queries.PendingRow, with_balance: bool) -> dict:
    order = row.order
    data = {
        'id': _id(order.id),
        'order_date': order.order_date.isoformat(),
        'customer': _customer(row),
        'total': money(order.total),
        'status': order.status,
        'payment_status': order.payment_status,
    }
    if with_balance:
        data['balance'] = money(order.balance)
    else:
        data['expected_delivery_date'] = (order.expected_delivery_date.isoformat()
                                          if order.expected_delivery_date else None)
    return data


def pending_data(report: queries.PendingReport) -> dict:
    return {
        'delivery': {'count': report.delivery.count,
                     'rows': [_pending_row(r, with_balance=False) for r in report.delivery.rows]},
        'collection': {'count': report.collection.count, 'balance_total': money(report.collection.balance_total),
                       'rows': [_pending_row(r, with_balance=True) for r in report.collection.rows]},
    }
