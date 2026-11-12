from odoo import models, fields, api
from odoo.exceptions import ValidationError

class MedicalPatientContract(models.Model):
    _name = 'medical.patient.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Ugovor pacijenta'
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Broj ugovora',
        required=True,
        tracking=True,
    )

    contract_type = fields.Selection(
        selection=[
            ('dependent', 'Zavisni korisnik'),
            ('independent', 'Samostalni korisnik'),
        ],
        string='Kategorija korisnika',
        tracking=True,
    )

    monthly_price = fields.Monetary(
        string='Ugovorena mjesečna cijena',
        currency_field='currency_id',
        tracking=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Valuta',
        default=lambda self: self.env.ref('base.BAM').id,
        required=True,
    )

    patient_id = fields.Many2one(
        'medical.patient',
        string='Pacijent',
        required=True,
        ondelete='restrict',
        tracking=True,
    )

    requester_id = fields.Many2one(
        'res.partner',
        string='Naručilac',
        ondelete='restrict',
        tracking=True,
    )

    contractor_id = fields.Many2one(
        'res.partner',
        string='Ugovarač',
        ondelete='restrict',
        tracking=True,
    )

    date_signed = fields.Date(
        string='Datum zaključenja ugovora',
        default=fields.Date.context_today,
        tracking=True,
    )

    date_start = fields.Date(
        string='Datum početka',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    date_end = fields.Date(
        string='Datum završetka',
        tracking=True,
    )

    state = fields.Selection(
        selection=[
            ('open', 'Otvoren'),
            ('closed', 'Zatvoren'),
        ],
        string='Status',
        required=True,
        default='open',
        tracking=True,
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
