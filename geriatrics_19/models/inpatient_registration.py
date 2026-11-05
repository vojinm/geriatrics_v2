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

    def write(self, vals):
        if "state" in vals:
            allowed_transitions = {
                "draft": {"hospitalized", "cancelled"},
                "hospitalized": {"discharged"},
                "discharged": set(),
                "cancelled": set(),
            }

            for record in self:
                new_state = vals["state"]

                if new_state == record.state:
                    continue

                if new_state not in allowed_transitions.get(record.state, set()):
                    raise UserError(
                        "Nedozvoljena promjena statusa hospitalizacije: "
                        f"{record.state} → {new_state}."
                    )
        if vals.get("state") == "cancelled":
            for record in self:
                reason = vals.get(
                    "cancellation_reason", record.cancellation_reason
                )
                if not reason or not reason.strip():
                    raise UserError(
                        "Morate unijeti razlog otkazivanja prijema."
                    )
        if vals.get("state") == "discharged":
            for record in self:
                reason = vals.get(
                    "discharge_reason", record.discharge_reason
                )
                if not reason or not reason.strip():
                    raise UserError(
                        "Morate unijeti razlog otpusta pacijenta."
                    )
        if "state" in vals or "patient_id" in vals:
            active_patient_ids = []

            for record in self:
                new_state = vals.get("state", record.state)
                patient_id = vals.get("patient_id", record.patient_id.id)

                if new_state != "hospitalized":
                    continue

                if patient_id in active_patient_ids:
                    raise UserError(
                        "Pacijent ne može imati dvije aktivne hospitalizacije."
                    )

                active_patient_ids.append(patient_id)

                existing = self.search([
                    ("patient_id", "=", patient_id),
                    ("state", "=", "hospitalized"),
                    ("id", "not in", self.ids),
                ], limit=1)

                if existing:
                    raise UserError(
                        "Ovaj pacijent već ima aktivnu hospitalizaciju."
                    )
                return super().write(vals)

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
