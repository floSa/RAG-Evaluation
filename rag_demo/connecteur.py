"""Le connecteur du RAG de démonstration (specs/CONTRAT.md, « Le connecteur ») : les six méthodes que le kit appelle
par leur nom. Il n'importe rien du kit."""

from rag_demo.rag import Rag


class Connecteur:
    def __init__(self, k: int | None = None):
        self.rag = Rag(k=k)

    def decrire(self) -> dict:
        return self.rag.decrire()

    def exporter_index(self):
        cles = ("chunk_id", "type_objet", "reference_source", "version_document", "page", "type_element",
                "droits_acces", "ordre", "texte", "version_index", "metadonnees")
        return ({k: c[k] for k in cles if k in c} for c in self.rag.chunks)

    def exporter_pages(self):
        return iter(self.rag.pages)

    def exporter_graphe(self, chemin):
        return None  # RAG vectoriel : pas de graphe

    def rechercher(self, question: str, profil: str, historique: list) -> list[dict]:
        return self.rag.rechercher(question, profil, historique)

    def repondre(self, question: str, profil: str, historique: list) -> dict:
        return self.rag.repondre(question, profil, historique)
