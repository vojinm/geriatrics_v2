from odoo import models, fields

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
