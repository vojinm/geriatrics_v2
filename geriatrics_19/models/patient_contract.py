from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MadicalPatientContract(models.Model):
    _name = 'medical.patient.contract'
    _description = 'Ugovor pacijenta'
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Broj ugovora',
        required=True,
    )

    patient_id = fields.Many2one(
        'medical.patient',
        string='Pacijent',
        required=True,
        ondelete='restrict',
    )

    requester_id = fields.Many2one(
        'res.partner',
        string='Naručilac',
        ondelete='restrict',
    )

    contractor_id = fields.Many2one(
        'res.partner',
        string='Ugovarač',
        ondelete='restrict',
    )

    date_start = fields.Date(
        string='Datum početka',
        required=True,
        default=fields.Date.context_today,
    )

    date_end = fields.Date(
        string='Datum završetka',
    )

    state = fields.Selection(
        selection=[
            ('open', 'Otvoren'),
            ('closed', 'Zatvoren'),
        ],
        string='Status',
        required=True,
        default='open',
    )

    note = fields.Text(
        string='Napomena',
    )

    _unique_open_contract_per_patient = models.UniqueIndex(
        "(patient_id) WHERE state = 'open'",
        "Pacijent već ima otvoren ugovor."
    )

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for contract in self:
            if contract.date_end and contract.date_start:
                if contract.date_end < contract.date_start:
                    raise ValidationError(
                        "Datum završetka ugovora ne može biti raniji od datuma početka."
                    )
    @api.constrains('state', 'date_end')
    def _check_closed_contract_date_end(self):
        for contract in self:
            if contract.state == 'closed' and not contract.date_end:
                raise ValidationError(
                    "Zatvoreni ugovor mora imati datum završetka."
                )
