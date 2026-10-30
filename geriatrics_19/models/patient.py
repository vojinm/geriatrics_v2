from odoo import models, fields, api
from odoo.exceptions import ValidationError

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
        readonly=False,
    )


    lastname = fields.Char(
        string='Prezime pacijenta',
        related='partner_id.lastname',
        readonly=False,
    )

    birthdate = fields.Date(
        string='Datum rođenja',
        related='partner_id.birthdate',
        readonly=False,
    )

    birth_place = fields.Char(
        string='Mjesto rođenja',
        related='partner_id.birth_place',
        readonly=False,
    )

    sex = fields.Selection(
        related='partner_id.sex',
        string='Pol',
        readonly=False,
    )

    phone = fields.Char(
        string='Telefon',
        related='partner_id.phone',
        readonly=False,
    )

    mobile = fields.Char(
        string='Mobilni telefon',
        related='partner_id.mobile',
        readonly=False,
    )

    email = fields.Char(
        string='E-mail',
        related='partner_id.email',
        readonly=False,
    )

    street = fields.Char(
        string='Ulica i broj',
        related='partner_id.street',
        readonly=False,
    )

    street2 = fields.Char(
        string='Dodatna adresa',
        related='partner_id.street2',
        readonly=False,
    )

    zip = fields.Char(
        string='Poštanski broj',
        related='partner_id.zip',
        readonly=False,
    )

    city = fields.Char(
        string='Grad',
        related='partner_id.city',
        readonly=False,
    )

    country_id = fields.Many2one(
        'res.country',
        string='Država',
        related='partner_id.country_id',
        readonly=False,
    )

    family_relation_ids = fields.One2many(
        'geriatrics.family.relation',
        'family_partner_id',
        string='Članovi porodice',
        related='partner_id.family_relation_ids',
        readonly=True,
    )

    _unique_partner = models.Constraint(
        'UNIQUE(partner_id)',
        'Ovaj kontakt je već registrovan kao pacijent.'
    )

    @api.model_create_multi
    def create(self, vals_list):
        partner_fields = [
            'name', 'lastname', 'birthdate', 'birth_place',
            'sex', 'phone', 'mobile', 'email',
            'street', 'street2', 'zip', 'city', 'country_id',
        ]

        for vals in vals_list:
            if not vals.get('partner_id'):
                partner_vals = {}

                for field_name in partner_fields:
                    if field_name in vals:
                        partner_vals[field_name] = vals.pop(field_name)

                if not partner_vals.get('name'):
                    raise ValueError("Ime pacijenta je obavezno.")

                partner = self.env['res.partner'].create(partner_vals)
                vals['partner_id'] = partner.id

        return super().create(vals_list)
