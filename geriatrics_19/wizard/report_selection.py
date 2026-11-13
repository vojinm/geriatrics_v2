import base64
from datetime import date
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from odoo import fields, models
from odoo.exceptions import UserError


MONTHS = [
    ("1", "Januar"),
    ("2", "Februar"),
    ("3", "Mart"),
    ("4", "April"),
    ("5", "Maj"),
    ("6", "Jun"),
    ("7", "Jul"),
    ("8", "Avgust"),
    ("9", "Septembar"),
    ("10", "Oktobar"),
    ("11", "Novembar"),
    ("12", "Decembar"),
]


class GeriatricsReportSelection(models.TransientModel):
    _name = "geriatrics.report.selection"
    _description = "Izbor izvještaja Gerijatrije"

    report_type = fields.Selection(
        [
            ("spisak_promjena", "Spisak promjena za period"),
        ],
        string="Vrsta izvještaja",
        required=True,
        default="spisak_promjena",
    )

    month = fields.Selection(
        MONTHS,
        string="Mjesec",
        required=True,
        default=lambda self: str(date.today().month),
    )

    year = fields.Integer(
        string="Godina",
        required=True,
        default=lambda self: date.today().year,
    )

    file_data = fields.Binary(
        string="Excel datoteka",
        readonly=True,
        attachment=False,
    )

    file_name = fields.Char(
        string="Naziv datoteke",
        readonly=True,
    )

    state = fields.Selection(
        [
            ("choose", "Izbor parametara"),
            ("get", "Preuzimanje izvještaja"),
        ],
        default="choose",
    )

    def _get_report_period(self):
        self.ensure_one()

        if not 1900 <= self.year <= 2100:
            raise UserError(
                "Godina mora biti između 1900. i 2100."
            )

        month = int(self.month)
        date_from = date(self.year, month, 1)

        if month == 12:
            date_to = date(self.year + 1, 1, 1)
        else:
            date_to = date(self.year, month + 1, 1)

        return date_from, date_to

    def _get_contract_and_death_data(self, date_from, date_to):
        """Prikuplja podatke za tri kategorije izvještaja."""

        Contract = self.env["medical.patient.contract"]
        Patient = self.env["medical.patient"]

        admitted_contracts = Contract.search([
            ("date_start", ">=", date_from),
            ("date_start", "<", date_to),
        ], order="date_start, id")

        deceased_patients = Patient.search([
            ("dod", ">=", date_from),
            ("dod", "<", date_to),
        ], order="dod, id")

        ended_contracts = Contract.search([
            ("date_end", ">=", date_from),
            ("date_end", "<", date_to),
        ], order="date_end, id")

        return {
            "primljeni": [
                (contract.patient_id.partner_id.display_name,
                 contract.date_start)
                for contract in admitted_contracts
            ],
            "umrli": [
                (patient.partner_id.display_name,
                 fields.Date.to_date(patient.dod))
                for patient in deceased_patients
            ],
            "napustili": [
                (contract.patient_id.partner_id.display_name,
                 contract.date_end)
                for contract in ended_contracts
            ],
        }

    def _get_absence_data(self, date_from, date_to):
        """Prikuplja završena i otvorena odsustva pacijenata."""

        Registration = self.env["medical.inpatient.registration"]

        absences = Registration.search([
            ("state", "=", "discharged"),
            ("discharge_reason", "in", ["bolnica", "odsutan"]),
            ("discharge_date", "!=", False),
            ("discharge_date", "<", date_to),
        ], order="discharge_date, id")

        result = {
            "u_bolnici": [],
            "i_dalje_u_bolnici": [],
            "odsutni": [],
            "i_dalje_odsutni": [],
        }

        for absence in absences:
            next_admission = Registration.search([
                ("patient_id", "=", absence.patient_id.id),
                ("state", "in", ["hospitalized", "discharged"]),
                ("hospitalization_date", ">", absence.discharge_date),
            ], order="hospitalization_date, id", limit=1)

            absence_start = absence.discharge_date
            absence_end = (
                next_admission.hospitalization_date
                if next_admission else False
            )

            patient_name = absence.patient_id.partner_id.display_name

            if absence.discharge_reason == "bolnica":
                finished_key = "u_bolnici"
                ongoing_key = "i_dalje_u_bolnici"
            else:
                finished_key = "odsutni"
                ongoing_key = "i_dalje_odsutni"

            if absence_end and date_from <= absence_end < date_to:
                result[finished_key].append((
                    patient_name,
                    f"od {absence_start:%d.%m.%Y} "
                    f"do {absence_end:%d.%m.%Y}"
                ))

            elif not absence_end and absence_start < date_from:
                result[ongoing_key].append((
                    patient_name,
                    f"od {absence_start:%d.%m.%Y}"
                ))

        return result

    def action_generate_report(self):
        self.ensure_one()

        if self.report_type != "spisak_promjena":
            raise UserError("Nepoznata vrsta izvještaja.")

        date_from, date_to = self._get_report_period()

        data = self._get_contract_and_death_data(date_from, date_to)
        data.update(self._get_absence_data(date_from, date_to))

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Spisak promjena"

        worksheet["A2"] = "JU Dom za starija lica"
        worksheet["A3"] = "BANJA LUKA"
        worksheet["B4"] = "SPISAK PROMJENA ZA PERIOD"

        month_name = dict(MONTHS)[self.month]
        worksheet["B5"] = f"{month_name.upper()} {self.year}."

        for cell_ref in ("A2", "A3", "B4", "B5"):
            worksheet[cell_ref].font = Font(
                name="Calibri", size=12, bold=True
            )

        worksheet.column_dimensions["A"].width = 34
        worksheet.column_dimensions["B"].width = 36

        sections = [
            ("PRIMLJENI", "primljeni"),
            ("UMRLI", "umrli"),
            ("U BOLNICI", "u_bolnici"),
            ("I DALJE U BOLNICI", "i_dalje_u_bolnici"),
            ("ODSUTNI", "odsutni"),
            ("I DALJE ODSUTNI", "i_dalje_odsutni"),
            ("NAPUSTILI", "napustili"),
        ]

        row = 7

        for section_title, section_key in sections:
            records = data.get(section_key, [])

            if not records:
                continue

            worksheet.merge_cells(
                start_row=row, start_column=1,
                end_row=row, end_column=2
            )

            heading = worksheet.cell(row=row, column=1)
            heading.value = section_title
            heading.font = Font(
                name="Calibri", bold=True, color="FFFFFF"
            )
            heading.fill = PatternFill(
                fill_type="solid", fgColor="365F91"
            )
            heading.alignment = Alignment(
                horizontal="left"
            )

            row += 1

            for patient_name, value in records:
                worksheet.cell(
                    row=row, column=1, value=patient_name
                )

                value_cell = worksheet.cell(
                    row=row, column=2
                )

                if isinstance(value, date):
                    value_cell.value = value
                    value_cell.number_format = "DD.MM.YYYY"
                else:
                    value_cell.value = value

                row += 1

            row += 2

        if row == 7:
            worksheet["A7"] = (
                "Nema evidentiranih promjena za izabrani period."
            )

        output = BytesIO()
        workbook.save(output)

        filename = (
            f"Spisak_promjena_{self.year}_"
            f"{int(self.month):02d}.xlsx"
        )

        self.write({
            "file_data": base64.b64encode(output.getvalue()),
            "file_name": filename,
            "state": "get",
        })

        return {
            "type": "ir.actions.act_window",
            "name": "Spisak promjena za period",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
