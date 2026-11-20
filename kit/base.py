"""La base relationnelle du kit (document 1, section 5), décrite avec SQLAlchemy.

SQLite pour le bac à sable ; PostgreSQL en changeant seulement l'adresse dans config/kit.yaml.
Les tables reprennent les champs de specs/CONTRAT.md. Chaque ligne du corpus porte sa
version_corpus : plusieurs versions du corpus cohabitent, et une évaluation renvoie à la sienne.
Écart assumé avec le schéma du document 1 : une table « corpus » (une ligne par version importée),
qui garde le contenu de corpus.json.
"""

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Corpus(Base):
    """Une version importée du corpus (contenu de corpus.json)."""

    __tablename__ = "corpus"
    version_corpus: Mapped[str] = mapped_column(String, primary_key=True)
    contrat: Mapped[str] = mapped_column(String)
    projet: Mapped[str] = mapped_column(String)
    date: Mapped[str] = mapped_column(String)
    fichier_source: Mapped[str] = mapped_column(String)
    colonnes_libres: Mapped[list] = mapped_column(JSON, default=list)


class Document(Base):
    __tablename__ = "documents"
    version_corpus: Mapped[str] = mapped_column(ForeignKey("corpus.version_corpus"), primary_key=True)
    reference_source: Mapped[str] = mapped_column(String, primary_key=True)
    titre: Mapped[str] = mapped_column(Text)
    type_document: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    date: Mapped[str | None] = mapped_column(String, nullable=True)
    format: Mapped[str] = mapped_column(String)
    nb_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    criticite: Mapped[str] = mapped_column(String)
    droits_acces: Mapped[str] = mapped_column(String)
    en_vigueur: Mapped[bool] = mapped_column(Boolean)
    remplace_par: Mapped[str | None] = mapped_column(String, nullable=True)
    selection: Mapped[str] = mapped_column(String)
    colonnes_libres: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Question(Base):
    __tablename__ = "questions"
    version_corpus: Mapped[str] = mapped_column(ForeignKey("corpus.version_corpus"), primary_key=True)
    question_id: Mapped[str] = mapped_column(String, primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    profil: Mapped[str] = mapped_column(String)
    redigee_par: Mapped[str] = mapped_column(String)
    type_reponse: Mapped[str] = mapped_column(String)
    reponse_dans_documents: Mapped[str] = mapped_column(String)
    reponse_est_dans: Mapped[str | None] = mapped_column(String, nullable=True)
    reponse_attendue: Mapped[str] = mapped_column(Text)
    points_cles: Mapped[list | None] = mapped_column(JSON, nullable=True)
    difficulte: Mapped[str] = mapped_column(String)
    frequence: Mapped[str] = mapped_column(String)
    gravite: Mapped[str] = mapped_column(String)
    reservee_decision: Mapped[bool] = mapped_column(Boolean)
    question_precedente: Mapped[str | None] = mapped_column(String, nullable=True)
    variante_de: Mapped[str | None] = mapped_column(String, nullable=True)
    annotateur: Mapped[str | None] = mapped_column(String, nullable=True)
    date: Mapped[str | None] = mapped_column(String, nullable=True)
    colonnes_libres: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Passage(Base):
    __tablename__ = "passages"
    version_corpus: Mapped[str] = mapped_column(ForeignKey("corpus.version_corpus"), primary_key=True)
    passage_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    question_id: Mapped[str] = mapped_column(String)
    reference_source: Mapped[str] = mapped_column(String)
    page: Mapped[str] = mapped_column(String)
    type_element: Mapped[str] = mapped_column(String)
    passage: Mapped[str] = mapped_column(Text)
    repond: Mapped[str] = mapped_column(String)


class PageOcr(Base):
    __tablename__ = "pages_ocr"
    version_corpus: Mapped[str] = mapped_column(ForeignKey("corpus.version_corpus"), primary_key=True)
    reference_source: Mapped[str] = mapped_column(String, primary_key=True)
    page: Mapped[str] = mapped_column(String, primary_key=True)
    texte_retape: Mapped[str] = mapped_column(Text)
    retape_par: Mapped[str | None] = mapped_column(String, nullable=True)
    relu_par: Mapped[str | None] = mapped_column(String, nullable=True)
    date: Mapped[str | None] = mapped_column(String, nullable=True)


class LienIndex(Base):
    """Un lien passage ↔ chunk, pour une version de l'index (écrit par le rattachement)."""

    __tablename__ = "liens_index"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_corpus: Mapped[str] = mapped_column(String)
    passage_id: Mapped[int] = mapped_column(Integer)
    chunk_id: Mapped[str] = mapped_column(String)
    version_index: Mapped[str] = mapped_column(String)
    mode: Mapped[str] = mapped_column(String)
    similarite: Mapped[float] = mapped_column(Float)


class Evaluation(Base):
    """Une évaluation : date, versions du RAG, du corpus et du kit (contenu d'evaluation.json)."""

    __tablename__ = "evaluations"
    evaluation_id: Mapped[str] = mapped_column(String, primary_key=True)
    date: Mapped[str] = mapped_column(String)
    version_corpus: Mapped[str] = mapped_column(String)
    version_kit: Mapped[str] = mapped_column(String)
    version_rag: Mapped[str] = mapped_column(String)
    rag: Mapped[dict] = mapped_column(JSON)
    juge: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    seuils: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Resultat(Base):
    """Un score d'une question, à un niveau, dans une évaluation (une ligne de resultats_par_question.csv)."""

    __tablename__ = "resultats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("evaluations.evaluation_id"))
    question_id: Mapped[str | None] = mapped_column(String, nullable=True)  # vide pour un score de document ou de chunk
    niveau: Mapped[int] = mapped_column(Integer)
    score: Mapped[str] = mapped_column(String)
    valeur: Mapped[float | None] = mapped_column(Float, nullable=True)       # un nombre…
    verdict: Mapped[str | None] = mapped_column(String, nullable=True)      # …ou un texte (juste, partielle, fausse)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Pour recalculer les scores globaux et leur ventilation depuis la base (écart assumé : colonnes en plus)
    objet: Mapped[str | None] = mapped_column(String, nullable=True)        # passage, document, chunk ou page évalué
    attributs: Mapped[dict | None] = mapped_column(JSON, nullable=True)    # axes de ventilation
    poids: Mapped[float | None] = mapped_column(Float, nullable=True)       # pour un score pondéré
    reservee: Mapped[bool] = mapped_column(Boolean, default=False)          # question réservée à la décision


def moteur(adresse: str):
    """Crée le moteur SQLAlchemy ; pour SQLite, crée le dossier du fichier si besoin."""
    if adresse.startswith("sqlite:///"):
        from pathlib import Path

        Path(adresse.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(adresse)


def init_base(adresse: str) -> list[str]:
    """Crée les tables absentes (sans toucher aux données existantes) et rend leurs noms."""
    m = moteur(adresse)
    Base.metadata.create_all(m)
    return sorted(Base.metadata.tables)
