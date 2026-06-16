"""QB indicator tables: fact_qualitaetsindikator, dim_qualitaetsindikator,
traegerschaft + lat/lon columns on dim_einrichtung.

Revision ID: 002
Revises: 001
Create Date: 2026-06-16
"""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─────────────────────────────────────────────
    # Extend core.dim_einrichtung
    # ─────────────────────────────────────────────
    op.execute("""
        CREATE TYPE core.traegerschaft_enum AS ENUM
        ('oeffentlich', 'freigemeinnuetzig', 'privat')
    """)
    op.execute("""
        ALTER TABLE core.dim_einrichtung
            ADD COLUMN traegerschaft core.traegerschaft_enum,
            ADD COLUMN lat NUMERIC(9, 6),
            ADD COLUMN lon NUMERIC(9, 6)
    """)

    # ─────────────────────────────────────────────
    # core.dim_qualitaetsindikator — G-BA indicator catalog
    # ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE core.dim_qualitaetsindikator (
            kennzahl_id         TEXT    PRIMARY KEY,
            bezeichnung         TEXT,
            leistungsbereich    TEXT,
            rechenregel         TEXT,
            datenquelle         TEXT,           -- 'QB' | 'DeQS'
            ist_planungsrelevant BOOLEAN
        )
    """)

    # Seed with key G-BA Qualitätsindikatoren
    op.execute("""
        INSERT INTO core.dim_qualitaetsindikator
            (kennzahl_id, bezeichnung, leistungsbereich, datenquelle, ist_planungsrelevant)
        VALUES
            ('54310',  'Sectio-Rate',
             'Geburtshilfe', 'QB', false),
            ('54311',  'Anwesenheit eines Facharztes bei Kaiserschnitt',
             'Geburtshilfe', 'QB', false),
            ('54312',  'E-E-Zeit bei dringlichem Kaiserschnitt ≤ 20 Minuten',
             'Geburtshilfe', 'QB', true),
            ('2075',   'Herzschrittmacher-Implantation: Indikation',
             'Herzschrittmacher', 'QB', true),
            ('2076',   'Herzschrittmacher-Implantation: Eingriffsdauer',
             'Herzschrittmacher', 'QB', false),
            ('50024',  'Hüft-TEP: Implantatfehllage/-fraktur',
             'Hüftgelenkersatz', 'QB', true),
            ('50023',  'Hüft-TEP: Endoprothesenwechsel und -komponentenwechsel',
             'Hüftgelenkersatz', 'QB', true),
            ('14004',  'Ambulant erworbene Pneumonie: Frühmobilisation',
             'Pneumonie', 'QB', false),
            ('14005',  'Ambulant erworbene Pneumonie: Blutkultur bei schwerer Pneumonie',
             'Pneumonie', 'QB', false),
            ('17014',  'Pflege: Sturzprophylaxe — Durchführung',
             'Pflege: Dekubitus/Sturz', 'QB', false),
            ('17015',  'Pflege: Dekubitusprophylaxe — Risikoassessment',
             'Pflege: Dekubitus/Sturz', 'QB', false),
            ('50052',  'Knie-TEP: Ungeplante Folgeoperation',
             'Kniegelenkersatz', 'QB', true),
            ('50042',  'Schulter-TEP: Ungeplante Folgeoperation',
             'Schultergelenkersatz', 'QB', false),
            ('12N1',   'Koronarangiographie: Indikation bei elektiver Koronarangiographie',
             'Koronarangiographie und PCI', 'QB', true),
            ('12N2',   'PCI: Leitlinienkonforme Indikation bei stabiler Angina pectoris',
             'Koronarangiographie und PCI', 'QB', true),
            ('10N1',   'Aortenklappenchirurgie: Nahtinsuffizienz nach Narbenhernienoperation',
             'Herzchirurgie', 'QB', false),
            ('DEK',    'Dekubitusprophylaxe: Neu aufgetretene Dekubitalulzera Grad 2–4',
             'Dekubitusprophylaxe', 'QB', true),
            ('NEO',    'Neonatologie: Sterblichkeit Frühgeborener 24.–31. SSW',
             'Neonatologie', 'QB', true)
    """)

    # ─────────────────────────────────────────────
    # core.fact_qualitaetsindikator (partitioned by berichtsjahr)
    # ─────────────────────────────────────────────
    op.execute("""
        CREATE TABLE core.fact_qualitaetsindikator (
            id                  BIGSERIAL,
            ik_nummer           CHAR(9)     NOT NULL,
            berichtsjahr        SMALLINT    NOT NULL,
            kennzahl_id         TEXT        NOT NULL
                                REFERENCES core.dim_qualitaetsindikator(kennzahl_id)
                                ON DELETE RESTRICT,
            leistungsbereich    TEXT,
            bezeichnung         TEXT,
            zaehler             INTEGER,
            nenner              INTEGER,
            ergebnis            NUMERIC(10, 4),
            referenzbereich_von NUMERIC(10, 4),
            referenzbereich_bis NUMERIC(10, 4),
            auffaellig          BOOLEAN,
            ist_planungsrelevant BOOLEAN,
            PRIMARY KEY (id, berichtsjahr)
        ) PARTITION BY RANGE (berichtsjahr)
    """)
    for year in range(2018, 2026):
        op.execute(f"""
            CREATE TABLE core.fact_qualitaetsindikator_{year}
            PARTITION OF core.fact_qualitaetsindikator
            FOR VALUES FROM ({year}) TO ({year + 1})
        """)

    op.execute("""
        CREATE INDEX idx_fqi_ik_jahr
        ON core.fact_qualitaetsindikator (ik_nummer, berichtsjahr)
    """)
    op.execute("""
        CREATE INDEX idx_fqi_kennzahl
        ON core.fact_qualitaetsindikator (kennzahl_id, berichtsjahr)
    """)
    op.execute("""
        CREATE INDEX idx_fqi_auffaellig
        ON core.fact_qualitaetsindikator (berichtsjahr, auffaellig)
        WHERE auffaellig = TRUE
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS core.fact_qualitaetsindikator CASCADE")
    op.execute("DROP TABLE IF EXISTS core.dim_qualitaetsindikator CASCADE")
    op.execute("""
        ALTER TABLE core.dim_einrichtung
            DROP COLUMN IF EXISTS traegerschaft,
            DROP COLUMN IF EXISTS lat,
            DROP COLUMN IF EXISTS lon
    """)
    op.execute("DROP TYPE IF EXISTS core.traegerschaft_enum CASCADE")
