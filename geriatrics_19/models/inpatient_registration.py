from odoo import api, fields, models
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

    medical_hospital_unit_id = fields.Many2one(
        'medical.hospital.unit',
        string='Odjel smještaja',
        ondelete='restrict',
    )

    bed_id = fields.Many2one(
        'medical.hospital.bed',
        string='Krevet',
        ondelete='restrict',
    )

    hospitalization_date = fields.Date(
        string="Datum prijema",
        default=fields.Date.context_today,
        required=True,
    )

    discharge_date = fields.Date(
        string="Datum otpusta",
    )

    discharge_reason = fields.Selection(
    [
        ("bolnica", "Na bolničkom liječenju"),
        ("odsutan", "Odsustvo"),
        ("napustio_centar", "Napustio centar"),
        ("preminuo", "Preminuo"),
    ],
    string="Razlog otpusta",
    )

    discharge_note = fields.Text(
        string="Napomena o otpustu",
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("state") == "hospitalized":
                raise UserError(
                    "Nova hospitalizacija mora prvo imati status "
                    "'Čeka prijem'. Koristite dugme za prijem pacijenta."
                )

            bed_id = vals.get("bed_id")
            unit_id = vals.get("medical_hospital_unit_id")

            if bed_id:
                if not unit_id:
                    raise UserError(
                        "Morate izabrati odjel smještaja "
                        "kada je dodijeljen krevet."
                    )

                bed = self.env["medical.hospital.bed"].browse(bed_id)

                if bed.ward_id.unit_id.id != unit_id:
                    raise UserError(
                        "Odabrani krevet ne pripada odjelu smještaja."
                    )

        return super().create(vals_list)

    def write(self, vals):
        if "bed_id" in vals and not vals["bed_id"]:
            for record in self:
                new_state = vals.get("state", record.state)

                if new_state == "hospitalized":
                    raise UserError(
                        "Ne možete ukloniti krevet iz aktivne "
                        "hospitalizacije. Izaberite drugi krevet "
                        "ili prvo otpustite pacijenta."
                    )
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
                if not reason:
                    raise UserError(
                        "Morate izabrati razlog otpusta pacijenta."
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

        if (
            vals.get("state") == "hospitalized"
            or (
                "bed_id" in vals
                and vals.get("state") not in ("discharged", "cancelled")
            )
        ):
            active_bed_ids = []

            for record in self:
                new_state = vals.get("state", record.state)
                bed_id = vals.get(
                    "bed_id",
                    record.bed_id.id,
                )

                if new_state != "hospitalized" or not bed_id:
                    continue

                if bed_id in active_bed_ids:
                    raise UserError(
                        "Isti krevet ne može biti dodijeljen "
                        "dvjema aktivnim hospitalizacijama."
                    )

                active_bed_ids.append(bed_id)

                existing = self.search([
                    ("bed_id", "=", bed_id),
                    ("state", "=", "hospitalized"),
                    ("id", "not in", self.ids),
                ], limit=1)

                if existing:
                    raise UserError(
                        "Odabrani krevet već koristi "
                        "drugi hospitalizovani pacijent."
                    )


                bed = self.env["medical.hospital.bed"].browse(bed_id)

                if bed.state in ("reserved", "na"):
                    raise UserError(
                        f"Krevet '{bed.name}' nije dostupan "
                        "za hospitalizaciju."
                    )

                if bed.state == "occupied":
                    if record.bed_id.id != bed_id:
                        raise UserError(
                            f"Krevet '{bed.name}' je već zauzet."
                        )

                    if record.state != "hospitalized":
                        raise UserError(
                            f"Krevet '{bed.name}' je već zauzet."
                        )

        if (
            "bed_id" in vals
            or "medical_hospital_unit_id" in vals
            or vals.get("state") == "hospitalized"
        ):
            for record in self:
                bed_id = vals.get("bed_id", record.bed_id.id)
                unit_id = vals.get(
                    "medical_hospital_unit_id",
                    record.medical_hospital_unit_id.id,
                )

                if not bed_id:
                    continue

                if not unit_id:
                    raise UserError(
                        "Morate izabrati odjel smještaja "
                        "kada je dodijeljen krevet."
                    )

                bed = self.env["medical.hospital.bed"].browse(bed_id)

                if bed.ward_id.unit_id.id != unit_id:
                    raise UserError(
                        "Odabrani krevet ne pripada odjelu smještaja."
                    )

        previous_beds = {
            record.id: (
                record.bed_id,
                record.state,
            )
            for record in self
        }

        result = super().write(vals)

        if "state" in vals or "bed_id" in vals:
            for record in self:
                old_bed, old_state = previous_beds[record.id]
                new_bed = record.bed_id

                if (
                    old_state == "hospitalized"
                    and old_bed
                    and (
                        record.state != "hospitalized"
                        or old_bed != new_bed
                    )
                ):

                    old_bed.state = "free"

                if (
                    record.state == "hospitalized"
                    and new_bed
                    and (
                        old_state != "hospitalized"
                        or old_bed != new_bed
                    )
                ):
                    new_bed.state = "occupied"

        return result

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

            if not record.discharge_reason:
                raise UserError(
                    "Morate izabrati razlog otpusta pacijenta."
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
