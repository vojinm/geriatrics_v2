from odoo import fields, models
from odoo.exceptions import UserError


class InpatientRegistration(models.Model):
    _name = "medical.inpatient.registration"
    _description = "Hospitalizacija pacijenta"
    _order = "hospitalization_date desc, id desc"

    name = fields.Char(
        string="Broj hospitalizacije",
        required=True,
    )

    patient_id = fields.Many2one(
        "medical.patient",
        string="Pacijent",
        required=True,
        ondelete="restrict",
    )

    hospitalization_date = fields.Date(
        string="Datum prijema",
        default=fields.Date.context_today,
        required=True,
    )

    discharge_date = fields.Date(
        string="Datum otpusta",
    )

    discharge_reason = fields.Text(
        string="Razlog otpusta",
    )

    cancellation_reason = fields.Text(
        string="Razlog otkazivanja",
    )

    state = fields.Selection(
        [
            ("draft", "Čeka prijem"),
            ("hospitalized", "Hospitalizovan"),
            ("discharged", "Otpušten"),
            ("cancelled", "Otkazan"),
        ],
        string="Status",
        default="draft",
        required=True,
    )

    def action_admit(self):
        for record in self:
            if record.state != "draft":
                raise UserError(
                    "Samo pacijent koji čeka prijem može biti hospitalizovan."
                )

            existing = self.search([
                ("patient_id", "=", record.patient_id.id),
                ("state", "=", "hospitalized"),
                ("id", "!=", record.id),
            ], limit=1)

            if existing:
                raise UserError(
                    "Ovaj pacijent već ima aktivnu hospitalizaciju."
                )

            record.state = "hospitalized"

    def action_discharge(self):
        for record in self:
            if record.state != "hospitalized":
                raise UserError(
                    "Samo hospitalizovan pacijent može biti otpušten."
                )

            if not record.discharge_reason or not record.discharge_reason.strip():
                raise UserError(
                    "Morate unijeti razlog otpusta pacijenta."
                )

            record.write({
                "state": "discharged",
                "discharge_date": fields.Date.context_today(record),
            })

    def unlink(self):
        for record in self:
            if record.state != "draft":
                raise UserError(
                    "Možete obrisati samo hospitalizaciju koja čeka prijem."
                )
        return super().unlink()

    def action_cancel(self):
        for record in self:
            if record.state != "draft":
                raise UserError(
                    "Možete otkazati samo hospitalizaciju koja čeka prijem."
                )

            if not record.cancellation_reason or not record.cancellation_reason.strip():
                raise UserError(
                    "Morate unijeti razlog otkazivanja prijema."
                )

            record.state = "cancelled"
