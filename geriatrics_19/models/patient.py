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

    mobile = fields.Char(
        string='Mobilni telefon',
        related='partner_id.mobile',
        readonly=True,
    )

    email = fields.Char(
        string='E-mail',
        related='partner_id.email',
        readonly=True,
    )

    street = fields.Char(
        string='Ulica i broj',
        related='partner_id.street',
        readonly=True,
    )

    street2 = fields.Char(
        string='Dodatna adresa',
        related='partner_id.street2',
        readonly=True,
    )

    zip = fields.Char(
        string='Poštanski broj',
        related='partner_id.zip',
        readonly=True,
    )

    city = fields.Char(
        string='Grad',
        related='partner_id.city',
        readonly=True,
    )

    country_id = fields.Many2one(
        'res.country',
        string='Država',
        related='partner_id.country_id',
        readonly=True,
    )

    _unique_partner = models.Constraint(
        'UNIQUE(partner_id)',
        'Ovaj kontakt je već registrovan kao pacijent.'
    )
