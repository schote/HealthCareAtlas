"""Full schema: dimensions, fact tables, mart, and raw landing tables.

Revision ID: 001
Revises:
Create Date: 2026-06-18
"""

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ENUM types ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TYPE core.versorgungsstufe_enum AS ENUM
        ('Grund', 'Regel', 'Schwerpunkt', 'Maximal')
    """)
    op.execute("""
        CREATE TYPE core.traegerschaft_enum AS ENUM
        ('oeffentlich', 'freigemeinnuetzig', 'privat')
    """)

    # ── core.dim_region ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE core.dim_region (
            ags             CHAR(8)  PRIMARY KEY,
            name            TEXT     NOT NULL,
            ebene           TEXT     NOT NULL,
            parent_ags      CHAR(8)  REFERENCES core.dim_region(ags),
            einwohner       INTEGER,
            anteil_65plus   NUMERIC(5,2),
            morbiditaet_idx NUMERIC(6,3)
        )
    """)

    # ── core.dim_einrichtung (SCD-2) ──────────────────────────────────────────
    op.execute("""
        CREATE TABLE core.dim_einrichtung (
            sk               BIGSERIAL   PRIMARY KEY,
            ik_nummer        CHAR(9)     NOT NULL,
            standort_id      TEXT        NOT NULL,
            name             TEXT,
            ags              CHAR(8)     REFERENCES core.dim_region(ags),
            versorgungsstufe core.versorgungsstufe_enum,
            traegerschaft    core.traegerschaft_enum,
            plz              CHAR(5),
            ort              TEXT,
            strasse          TEXT,
            betten           INTEGER,
            lat              NUMERIC(9, 6),
            lon              NUMERIC(9, 6),
            valid_from       DATE        NOT NULL,
            valid_to         DATE        NOT NULL DEFAULT '9999-12-31',
            is_current       BOOLEAN     NOT NULL DEFAULT TRUE
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_einrichtung_current
        ON core.dim_einrichtung (ik_nummer, standort_id)
        WHERE is_current
    """)
    op.execute("""
        CREATE INDEX idx_einrichtung_ik ON core.dim_einrichtung (ik_nummer)
    """)

    # ── core.dim_zeit ─────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE core.dim_zeit (
            berichtsjahr SMALLINT NOT NULL,
            quartal      SMALLINT NOT NULL CHECK (quartal BETWEEN 1 AND 4),
            PRIMARY KEY (berichtsjahr, quartal)
        )
    """)

    # ── core.dim_fachabteilung ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE core.dim_fachabteilung (
            fab_id      INTEGER PRIMARY KEY,
            bezeichnung TEXT    NOT NULL,
            ldkr_code   TEXT
        )
    """)

    # ── core.dim_qualitaetsindikator — G-BA indicator catalog ─────────────────
    op.execute("""
        CREATE TABLE core.dim_qualitaetsindikator (
            kennzahl_id          TEXT    PRIMARY KEY,
            bezeichnung          TEXT,
            leistungsbereich     TEXT,
            rechenregel          TEXT,
            datenquelle          TEXT,
            ist_planungsrelevant BOOLEAN
        )
    """)
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

    # ── core.config_weights ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE core.config_weights (
            version     TEXT         NOT NULL,
            metric_key  TEXT         NOT NULL,
            weight      NUMERIC(5,4) NOT NULL CHECK (weight >= 0 AND weight <= 1),
            valid_from  DATE         NOT NULL,
            PRIMARY KEY (version, metric_key)
        )
    """)
    op.execute("""
        INSERT INTO core.config_weights (version, metric_key, weight, valid_from) VALUES
        ('v2.0', 'quality',  0.70, '2026-06-18'),
        ('v2.0', 'casemix',  0.30, '2026-06-18')
    """)

    # ── core.fact_qualitaet (partitioned) ─────────────────────────────────────
    op.execute("""
        CREATE TABLE core.fact_qualitaet (
            id                BIGSERIAL,
            ik_nummer         CHAR(9)   NOT NULL,
            berichtsjahr      SMALLINT  NOT NULL,
            fab_id            INTEGER   REFERENCES core.dim_fachabteilung(fab_id),
            smr               NUMERIC(4,2),
            smr_adj           NUMERIC(4,2),
            komplikationsrate NUMERIC(5,3),
            hygiene_score     SMALLINT  CHECK (hygiene_score BETWEEN 0 AND 100),
            PRIMARY KEY (id, berichtsjahr)
        ) PARTITION BY RANGE (berichtsjahr)
    """)
    for year in range(2018, 2026):
        op.execute(f"""
            CREATE TABLE core.fact_qualitaet_{year}
            PARTITION OF core.fact_qualitaet
            FOR VALUES FROM ({year}) TO ({year + 1})
        """)
    op.execute("""
        CREATE INDEX idx_fq_ik_jahr ON core.fact_qualitaet (ik_nummer, berichtsjahr)
    """)

    # ── core.fact_qualitaetsindikator (partitioned) ───────────────────────────
    op.execute("""
        CREATE TABLE core.fact_qualitaetsindikator (
            id                   BIGSERIAL,
            ik_nummer            CHAR(9)      NOT NULL,
            berichtsjahr         SMALLINT     NOT NULL,
            kennzahl_id          TEXT         NOT NULL
                                 REFERENCES core.dim_qualitaetsindikator(kennzahl_id)
                                 ON DELETE RESTRICT,
            leistungsbereich     TEXT,
            bezeichnung          TEXT,
            zaehler              INTEGER,
            nenner               INTEGER,
            ergebnis             NUMERIC(10, 4),
            referenzbereich_von  NUMERIC(10, 4),
            referenzbereich_bis  NUMERIC(10, 4),
            auffaellig           BOOLEAN,
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

    # ── core.fact_drg (partitioned) ───────────────────────────────────────────
    op.execute("""
        CREATE TABLE core.fact_drg (
            id            BIGSERIAL,
            ik_nummer     CHAR(9)      NOT NULL,
            berichtsjahr  SMALLINT     NOT NULL,
            drg_code      TEXT         NOT NULL,
            fallzahl      INTEGER,
            verweildauer  NUMERIC(5,2),
            casemix_index NUMERIC(5,3),
            PRIMARY KEY (id, berichtsjahr)
        ) PARTITION BY RANGE (berichtsjahr)
    """)
    for year in range(2018, 2026):
        op.execute(f"""
            CREATE TABLE core.fact_drg_{year}
            PARTITION OF core.fact_drg
            FOR VALUES FROM ({year}) TO ({year + 1})
        """)
    op.execute("""
        CREATE INDEX idx_fdrg_ik_jahr ON core.fact_drg (ik_nummer, berichtsjahr)
    """)

    # ── core.fact_kapazitaet (partitioned) ────────────────────────────────────
    op.execute("""
        CREATE TABLE core.fact_kapazitaet (
            id               BIGSERIAL,
            ik_nummer        CHAR(9)     NOT NULL,
            berichtsjahr     SMALLINT    NOT NULL,
            betten           INTEGER,
            bettenauslastung NUMERIC(5,2),
            PRIMARY KEY (id, berichtsjahr)
        ) PARTITION BY RANGE (berichtsjahr)
    """)
    for year in range(2018, 2026):
        op.execute(f"""
            CREATE TABLE core.fact_kapazitaet_{year}
            PARTITION OF core.fact_kapazitaet
            FOR VALUES FROM ({year}) TO ({year + 1})
        """)

    # ── core.fact_ppugv (partitioned) ─────────────────────────────────────────
    op.execute("""
        CREATE TABLE core.fact_ppugv (
            id                BIGSERIAL,
            ik_nummer         CHAR(9)    NOT NULL,
            berichtsjahr      SMALLINT   NOT NULL,
            quartal           SMALLINT   NOT NULL CHECK (quartal BETWEEN 1 AND 4),
            bereich           TEXT       NOT NULL,
            schichten_konform NUMERIC(5,2),
            patient_pflege    NUMERIC(5,2),
            untergrenze       NUMERIC(5,2),
            PRIMARY KEY (id, berichtsjahr)
        ) PARTITION BY RANGE (berichtsjahr)
    """)
    for year in range(2018, 2026):
        op.execute(f"""
            CREATE TABLE core.fact_ppugv_{year}
            PARTITION OF core.fact_ppugv
            FOR VALUES FROM ({year}) TO ({year + 1})
        """)

    # ── core.fact_mindestmenge (partitioned) ──────────────────────────────────
    op.execute("""
        CREATE TABLE core.fact_mindestmenge (
            id           BIGSERIAL,
            ik_nummer    CHAR(9)    NOT NULL,
            berichtsjahr SMALLINT   NOT NULL,
            ops_code     TEXT       NOT NULL,
            soll         INTEGER,
            ist          INTEGER,
            status       JSONB,
            PRIMARY KEY (id, berichtsjahr)
        ) PARTITION BY RANGE (berichtsjahr)
    """)
    for year in range(2018, 2026):
        op.execute(f"""
            CREATE TABLE core.fact_mindestmenge_{year}
            PARTITION OF core.fact_mindestmenge
            FOR VALUES FROM ({year}) TO ({year + 1})
        """)
    op.execute("""
        CREATE INDEX idx_fmm_status ON core.fact_mindestmenge USING GIN (status)
    """)

    # ── core.fact_erreichbarkeit ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE core.fact_erreichbarkeit (
            id                BIGSERIAL   PRIMARY KEY,
            standort_id       TEXT        NOT NULL,
            ags               CHAR(8)     REFERENCES core.dim_region(ags),
            fahrzeit_maxvers  NUMERIC(6,2),
            einwohner_einzug  INTEGER
        )
    """)
    op.execute("""
        CREATE INDEX idx_ferr_standort ON core.fact_erreichbarkeit (standort_id)
    """)

    # ── mart.einrichtung_kpi ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE mart.einrichtung_kpi (
            ik_nummer     CHAR(9)      NOT NULL,
            berichtsjahr  SMALLINT     NOT NULL,
            quality_score NUMERIC(4,2),
            casemix_index NUMERIC(5,3),
            def_index     NUMERIC(5,2) NOT NULL,
            konfidenz     NUMERIC(3,2) NOT NULL,
            datenstand    DATE         NOT NULL,
            PRIMARY KEY (ik_nummer, berichtsjahr)
        )
    """)
    op.execute("""
        CREATE INDEX idx_kpi_def_index ON mart.einrichtung_kpi (def_index DESC)
    """)
    op.execute("""
        CREATE INDEX idx_kpi_berichtsjahr ON mart.einrichtung_kpi (berichtsjahr)
    """)

    # ── mart.v_deficit_rank (materialized view) ───────────────────────────────
    op.execute("""
        CREATE MATERIALIZED VIEW mart.v_deficit_rank AS
        SELECT
            'einrichtung'           AS ebene,
            k.ik_nummer             AS entity_id,
            e.name                  AS name,
            'def_index'             AS metric_key,
            k.def_index             AS score,
            RANK() OVER (
                PARTITION BY k.berichtsjahr
                ORDER BY k.def_index DESC
            )                       AS rang,
            k.berichtsjahr
        FROM mart.einrichtung_kpi k
        JOIN core.dim_einrichtung e
            ON e.ik_nummer = k.ik_nummer AND e.is_current
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_deficit_rank
        ON mart.v_deficit_rank (ebene, metric_key, entity_id, berichtsjahr)
    """)

    # ── raw landing tables ────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE raw.qualitaetsbericht (
            id           BIGSERIAL   PRIMARY KEY,
            berichtsjahr SMALLINT    NOT NULL,
            source_file  TEXT        NOT NULL,
            file_hash    CHAR(64)    NOT NULL,
            ik_nummer    CHAR(9),
            raw_xml      TEXT        NOT NULL,
            parsed_json  JSONB,
            ingested_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX idx_qb_ingested_brin ON raw.qualitaetsbericht
        USING BRIN (ingested_at)
    """)
    op.execute("""
        CREATE INDEX idx_qb_jahr ON raw.qualitaetsbericht (berichtsjahr)
    """)

    op.execute("""
        CREATE TABLE raw.drg_fallzahlen (
            id            BIGSERIAL   PRIMARY KEY,
            ik_nummer     TEXT,
            standort_id   TEXT,
            drg_code      TEXT,
            fallzahl      TEXT,
            verweildauer  TEXT,
            casemix_index TEXT,
            berichtsjahr  SMALLINT    NOT NULL,
            source_file   TEXT        NOT NULL,
            ingested_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX idx_drg_ingested_brin ON raw.drg_fallzahlen USING BRIN (ingested_at)
    """)

    op.execute("""
        CREATE TABLE raw.ppugv (
            id           BIGSERIAL   PRIMARY KEY,
            berichtsjahr SMALLINT    NOT NULL,
            quartal      SMALLINT    NOT NULL,
            source_file  TEXT        NOT NULL,
            ingested_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE INDEX idx_ppugv_ingested_brin ON raw.ppugv USING BRIN (ingested_at)
    """)


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mart.v_deficit_rank CASCADE")
    op.execute("DROP TABLE IF EXISTS mart.einrichtung_kpi CASCADE")
    op.execute("DROP TABLE IF EXISTS raw.ppugv CASCADE")
    op.execute("DROP TABLE IF EXISTS raw.drg_fallzahlen CASCADE")
    op.execute("DROP TABLE IF EXISTS raw.qualitaetsbericht CASCADE")
    op.execute("DROP TABLE IF EXISTS core.fact_erreichbarkeit CASCADE")
    op.execute("DROP TABLE IF EXISTS core.fact_mindestmenge CASCADE")
    op.execute("DROP TABLE IF EXISTS core.fact_ppugv CASCADE")
    op.execute("DROP TABLE IF EXISTS core.fact_kapazitaet CASCADE")
    op.execute("DROP TABLE IF EXISTS core.fact_drg CASCADE")
    op.execute("DROP TABLE IF EXISTS core.fact_qualitaetsindikator CASCADE")
    op.execute("DROP TABLE IF EXISTS core.fact_qualitaet CASCADE")
    op.execute("DROP TABLE IF EXISTS core.config_weights CASCADE")
    op.execute("DROP TABLE IF EXISTS core.dim_qualitaetsindikator CASCADE")
    op.execute("DROP TABLE IF EXISTS core.dim_fachabteilung CASCADE")
    op.execute("DROP TABLE IF EXISTS core.dim_zeit CASCADE")
    op.execute("DROP TABLE IF EXISTS core.dim_einrichtung CASCADE")
    op.execute("DROP TABLE IF EXISTS core.dim_region CASCADE")
    op.execute("DROP TYPE IF EXISTS core.traegerschaft_enum CASCADE")
    op.execute("DROP TYPE IF EXISTS core.versorgungsstufe_enum CASCADE")
