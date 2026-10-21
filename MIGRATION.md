# GERIJATRIJA – Plan migracije Odoo 8 → Odoo 19

## 1. Osnovni principi

- `res.partner` predstavlja jedinstvenu evidenciju osoba i institucija.
- `medical.patient` sadrži podatke specifične za pacijenta.
- Porodične veze evidentiraju se zasebnim zapisima koji povezuju kontakte.
- Ugovori se evidentiraju zasebno i povezuju s pacijentom, ugovaračem i podnosiocem zahtjeva.
- Postojeći podaci i istorijske veze moraju biti sačuvani.
- Isti kontakt ne smije biti dupliran zbog različitih uloga.

## 2. Rezultati analize stare baze

| Podatak | Rezultat |
|---|---:|
| Pacijenti | 2.394 |
| Različiti poslovni brojevi pacijenata | 2.383 |
| Pacijenti s porodičnim vezama | 2.228 |
| Porodične veze (ranija analiza) | 5.127 |
| Jedinstveni kontakti članova porodice | 5.163 |
| Jedinstveni ugovarači | 2.048 |
| Kontakti u obje uloge | 497 |
| Različiti kontakti u ove dvije grupe | 6.714 |

Napomena: Broj porodičnih veza i broj različitih kontakata potiču iz različitih upita. Njihovu međusobnu razliku ne treba tumačiti bez dodatne provjere.

## 3. Mapiranje modela i polja

### Pacijenti

| Odoo 8 | Odoo 19 |
|---|---|
| `medical.patient.name` | `medical.patient.partner_id` |
| `medical.patient.patient_id` | `medical.patient.patient_number` |
| `medical.patient.sex` | `res.partner.sex` |

Poslovni broj pacijenta nije isto što i interni ID zapisa.

### Pol pacijenta

| Odoo 8 | Odoo 19 |
|---|---|
| `f` | `female` |
| `m` | `male` |

U staroj bazi evidentirano je 1.441 pacijentkinja i 953 pacijenta. Nema praznih vrijednosti pola.

### Lični podaci

U Odoo 19 proširujemo `res.partner` poljima:

- `birthdate` – `Date`
- `lastname` – `Char`
- `sex` – `Selection`

Staro polje `res_partner.birthdate` je tekstualnog tipa. Prije migracije potrebno je provjeriti i pravilno pretvoriti postojeće vrijednosti.

### Ugovori

U starom modelu `medical.patient.contract` postoje veze:

- `partner_id` – kontakt pacijenta
- `partner_contractor_id` – ugovarač
- `partner_requested_id` – podnosilac zahtjeva

Ugovarače treba preuzimati iz ugovora, a ne iz gotovo nekorištenog polja `medical_patient.contractor_id`.

## 4. Pravila koja se moraju poštovati

1. Ne kreirati duplikate `res.partner` zapisa za osobe koje imaju više uloga.
2. Ne uvoditi jedinstvenost poslovnog broja pacijenta dok se ne istraže postojeći duplikati.
3. Sačuvati mapiranje starih i novih internih ID-jeva.
4. Sačuvati porodične, ugovorne i druge istorijske veze.
5. Ne razdvajati automatski ime i prezime bez provjerenih pravila.
6. Ne uvoditi obavezna polja koja bi onemogućila migraciju postojećih podataka.
7. Zaštititi osjetljive lične i medicinske podatke odgovarajućim pravima pristupa.
8. Obezbijediti najviše jedan aktivan ugovor po pacijentu; isti ugovarač može imati više aktivnih ugovora za različite pacijente.

## 5. Otvorena pitanja

- Istražiti duplikate poslovnih brojeva pacijenata.
- Definisati postupak prenosa i mapiranja internih ID-jeva.
- Provjeriti formate datuma prije migracije.
- Definisati migraciju porodičnih veza, ugovora i medicinske istorije.
- Definisati validacije i testove nakon migracije.

## 6. Status

Dokument se dopunjava tokom razvoja modula `geriatrics_19`. Nijedno pravilo migracije ne treba smatrati implementiranim samo zato što je dokumentovano.

## 7. JMBG i datum rođenja – potvrđena analiza

### Izvor podataka

Stvarni Odoo 8 modul: hms_geriatrics (8.0.1.00).
Izvorni kod: C:\odoo8ger\addons\hms_geriatrics.

JMBG je izračunato polje medical.patient.jmbg,
koje čita i upisuje vrijednost u res.partner.ref.

Migracioni izvor:
medical_patient.name -> res_partner.id -> res_partner.ref

### Rezultati

- Ukupno pacijenata: 2394
- Popunjen JMBG/ref: 2324
- Bez JMBG-a: 70
- Različitih popunjenih vrijednosti: 2324
- Vrijednosti sa tačno 13 cifara: 2292
- Vrijednosti neispravnog formata: 32
- Pacijenti s datumom rođenja (medical_patient.dob): 2394

### Pravila migracije

- Sačuvati sve izvorne JMBG vrijednosti.
- Ne odbacivati niti automatski ispravljati 32 problematične vrijednosti.
- Ne generisati JMBG za pacijente kojima nedostaje.
- Datum rođenja prenijeti iz medical_patient.dob
  u res.partner.birthdate odgovarajućeg kontakta.
- JMBG ne smještati automatski u standardno res.partner.ref.
- Prije implementacije definisati sigurno čuvanje JMBG-a,
  prava pristupa i postupak validacije.