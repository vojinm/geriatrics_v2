from odoo import fields, models
from odoo.exceptions import UserError


class MedicalHospitalBed(models.Model):
    _name = 'medical.hospital.bed'
    _description = 'Krevet zdravstvene ustanove'
    _order = 'name'

    name = fields.Char(
        string='Naziv / oznaka kreveta',
        required=True,
    )

    ward_id = fields.Many2one(
        'medical.hospital.ward',
        string='Soba',
        required=True,
        ondelete='restrict',
    )

    bed_type = fields.Selection(
        [
            ('gatch', 'Bolnički krevet'),
            ('electric', 'Električni krevet'),
            ('stretcher', 'Nosila'),
            ('low', 'Niski krevet'),
            ('low_air_loss', 'Antidekubitalni krevet'),
            ('circo_electric', 'Rotacioni električni krevet'),
            ('clinitron', 'Clinitron krevet'),
        ],
        string='Tip kreveta',
    )

    telephone_number = fields.Char(
        string='Telefonski broj',
    )

    state = fields.Selection(
        [
            ('free', 'Slobodan'),
            ('reserved', 'Rezervisan'),
            ('occupied', 'Zauzet'),
            ('na', 'Nije dostupan'),
        ],
        string='Status',
        default='free',
        required=True,
    )

    extra_info = fields.Text(
        string='Dodatne informacije',
    )


    def write(self, vals):
        if vals.get("state") in ("free", "reserved", "na"):
            for bed in self:
                active = self.env[
                    "medical.inpatient.registration"
                ].search([
                    ("bed_id", "=", bed.id),
                    ("state", "=", "hospitalized"),
                ], limit=1)

                if active:
                    raise UserError(
                        f"Krevet '{bed.name}' trenutno koristi "
                        "hospitalizovani pacijent. "
                        "Prvo izvršite otpust ili premještaj pacijenta."
                    )

        return super().write(vals)
