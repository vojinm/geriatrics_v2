from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def init(self):
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                res_partner_legacy_id_unique_idx
            ON res_partner (legacy_id)
            WHERE legacy_id IS NOT NULL AND legacy_id <> 0
        """)

    patient_id = fields.One2many(
        'medical.patient',
        'partner_id',
        string='Pacijent',
    )

    birthdate = fields.Date(
        string='Datum rođenja',
    )

    lastname = fields.Char(
        string='Prezime',
    )

    sex = fields.Selection(
        selection=[
            ('male', 'Muško'), 
            ('female', 'Žensko')
        ],
        string='Pol',
    )

    mobile = fields.Char(string="Mobilni telefon")

    legacy_id = fields.Integer(
        string='ID partnera u Odoo 8',
        copy=False,
        index=True,
    )

