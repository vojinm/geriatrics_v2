from odoo import fields, models


class MedicalHospitalWard(models.Model):
    _name = 'medical.hospital.ward'
    _description = 'Soba zdravstvene ustanove'
    _order = 'name'

    name = fields.Char(
        string='Naziv / broj sobe',
        required=True,
    )

    institution_id = fields.Many2one(
        'res.partner',
        string='Ustanova',
        ondelete='restrict',
    )

    building_id = fields.Many2one(
        'medical.hospital.building',
        string='Objekat',
        ondelete='restrict',
    )

    unit_id = fields.Many2one(
        'medical.hospital.unit',
        string='Odjel',
        ondelete='restrict',
    )

    floor = fields.Integer(
        string='Sprat',
    )

    number_of_beds = fields.Integer(
        string='Broj kreveta',
        default=1,
    )

    gender = fields.Selection(
        [
            ('men', 'Muška'),
            ('women', 'Ženska'),
            ('unisex', 'Mješovita'),
        ],
        string='Namjena sobe',
        default='unisex',
        required=True,
    )

    state = fields.Selection(
        [
            ('beds_available', 'Ima slobodnih kreveta'),
            ('full', 'Popunjena'),
            ('na', 'Nije dostupna'),
        ],
        string='Status',
        default='beds_available',
    )

    private = fields.Boolean(string='Privatna soba')
    bio_hazard = fields.Boolean(string='Biološka opasnost')
    telephone = fields.Boolean(string='Telefon')
    ac = fields.Boolean(string='Klima uređaj')
    private_bathroom = fields.Boolean(string='Privatno kupatilo')
    guest_sofa = fields.Boolean(string='Kauč za goste')
    tv = fields.Boolean(string='Televizor')
    internet = fields.Boolean(string='Internet')
    refrigerator = fields.Boolean(string='Frižider')
    microwave = fields.Boolean(string='Mikrotalasna pećnica')

    extra_info = fields.Text(
        string='Dodatne informacije',
    )
