from odoo import models, fields, api

class MedicalPatient(models.Model):
    _name = 'medical.patient'
    _description = 'Pacijent'

    patient_number = fields.Char(
        string='Broj pacijenta',
        required=True,
        index=True,
    )

    jmbg = fields.Char(
        string='JMBG',
        groups='geriatrics_19.group_patient_sensitive_data',
        copy=False,
    )

    legacy_id = fields.Integer(
        string='Odoo 8 ID pacijenta',
        index=True,
        copy=False,
    )

    id_number = fields.Char(
        string='Broj licnog dokumenta',
        groups='geriatrics_19.group_patient_sensitive_data',
    )

    active = fields.Boolean(
        string='Aktivan',
        default=True,
    )
    
    partner_id = fields.Many2one(
        'res.partner', 
        string='Kontakt', 
        required=True, 
        ondelete='restrict'
    )

    name = fields.Char(
        string='Ime pacijenta',
        related='partner_id.name',
        readonly=True,
    )


    lastname = fields.Char(
        string='Prezime pacijenta',
        related='partner_id.lastname',
        readonly=True,
    )

    birthdate = fields.Date(
        string='Datum rođenja',
        related='partner_id.birthdate',
        readonly=True,
    )

    birth_place = fields.Char(
        string='Mjesto rođenja',
        related='partner_id.birth_place',
        readonly=True,
    )

    sex = fields.Selection(
        related='partner_id.sex',
        string='Pol',
        readonly=True,
    )

    phone = fields.Char(
        string='Telefon',
        related='partner_id.phone',
        readonly=True,
    )

    _unique_partner = models.Constraint(
        'UNIQUE(partner_id)',
        'Ovaj kontakt je već registrovan kao pacijent.'
    )
