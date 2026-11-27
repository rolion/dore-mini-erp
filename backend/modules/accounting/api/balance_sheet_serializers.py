"""Serializadores del balance general: validan forma y tipos; el cálculo lo hace el dominio."""
from rest_framework import serializers

from modules.accounting.application.balance_sheet import BalanceSheetReport
from modules.accounting.domain.balance_sheet import Amounts


class BalanceSheetFiltersSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


def _amounts(amounts: Amounts) -> dict:
    return {'opening': str(amounts.opening), 'movement': str(amounts.movement), 'closing': str(amounts.closing)}


def serialize_balance_sheet(report: BalanceSheetReport) -> dict:
    sections = []
    for section in report.sheet.sections:
        data = {'key': section.key, 'total': _amounts(section.total),
                'rows': [{'account_id': str(r.account_id), 'code': r.code, 'name': r.name, 'is_active': r.is_active,
                          **_amounts(r.amounts)} for r in section.rows]}
        if section.previous_result is not None and section.period_result is not None:
            data['previous_result'] = _amounts(section.previous_result)
            data['period_result'] = _amounts(section.period_result)
        sections.append(data)
    totals = report.sheet.totals
    return {'date_from': report.date_from, 'date_to': report.date_to, 'has_opening': report.date_from is not None,
            'sections': sections,
            'totals': {'assets': str(totals.assets), 'liabilities': str(totals.liabilities),
                       'equity': str(totals.equity), 'liabilities_and_equity': str(totals.liabilities_and_equity),
                       'difference': str(totals.difference), 'balanced': totals.balanced,
                       'unclassified_balance': str(totals.unclassified_balance)}}
