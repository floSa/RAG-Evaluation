"""Fabrique les PDF du corpus d'exemple à partir des contenus JSON (format_contenus.md).

- PDF natif : texte, titres, listes, tableaux, figures dessinées (reportlab).
- PDF scanné : la page est d'abord dessinée, puis rendue en image, abîmée (rotation, bruit, flou,
  compression) et remise en PDF : il ne contient plus aucun texte, seulement des images.
- Fiche de base de données : export « champ : valeur » sur une page.

Chaque page du JSON donne exactement une page du PDF (le contenu est réduit s'il déborde).
Usage : uv run --group fabrication python corpus/exemple/fabrication/fabriquer_pdf.py
"""

import io
import json
import random
import sys
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageFilter
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Frame, KeepInFrame, ListFlowable, ListItem, Paragraph, Spacer, Table,
                                TableStyle)
from reportlab.pdfgen import canvas

ICI = Path(__file__).resolve().parent
CONTENUS = ICI / "contenus"
SOURCES = ICI.parent / "sources"

pdfmetrics.registerFont(TTFont("Sans", ICI / "polices" / "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Gras", ICI / "polices" / "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Mono", ICI / "polices" / "DejaVuSansMono.ttf"))

LARGEUR, HAUTEUR = A4
MARGE = 20 * mm


def styles(police: str, gras: str) -> dict:
    """Styles de texte ; un document scanné utilise une police de machine à écrire."""
    return {
        "titre_doc": ParagraphStyle("titre_doc", fontName=gras, fontSize=15, leading=19, spaceAfter=8),
        "titre1": ParagraphStyle("titre1", fontName=gras, fontSize=12, leading=15, spaceBefore=6, spaceAfter=4),
        "titre2": ParagraphStyle("titre2", fontName=gras, fontSize=10.5, leading=13, spaceBefore=4, spaceAfter=3),
        "texte": ParagraphStyle("texte", fontName=police, fontSize=10, leading=13.5, spaceAfter=4),
        "cellule": ParagraphStyle("cellule", fontName=police, fontSize=9, leading=11),
        "entete": ParagraphStyle("entete", fontName=gras, fontSize=9, leading=11),
        "legende": ParagraphStyle("legende", fontName=police, fontSize=9, leading=11, spaceBefore=3, spaceAfter=6),
    }


def echapper(texte: str) -> str:
    """Échappe les caractères spéciaux du balisage de reportlab."""
    return texte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def figure(bloc: dict, police: str) -> Drawing:
    """Dessine une figure : boîtes rangées par couches (sources en haut), flèches étiquetées."""
    boites = {b["id"]: b["texte"] for b in bloc["boites"]}
    liens = bloc["liens"]
    # profondeur de chaque boîte : la plus longue chaîne de liens qui y arrive
    profondeur = {i: 0 for i in boites}
    for _ in boites:
        for de, vers, _etiquette in liens:
            profondeur[vers] = max(profondeur[vers], profondeur[de] + 1)
    couches: dict[int, list[str]] = {}
    for i in boites:
        couches.setdefault(profondeur[i], []).append(i)
    largeur = LARGEUR - 2 * MARGE
    l_boite, h_boite, ecart_v = 120, 34, 46
    hauteur = len(couches) * (h_boite + ecart_v)
    d = Drawing(largeur, hauteur)
    centres = {}
    for n, ids in sorted(couches.items()):
        y = hauteur - (n + 1) * (h_boite + ecart_v) + ecart_v / 2
        pas = largeur / len(ids)
        for k, i in enumerate(ids):
            x = pas * k + (pas - l_boite) / 2
            d.add(Rect(x, y, l_boite, h_boite, fillColor=colors.whitesmoke, strokeColor=colors.black))
            mots, lignes, ligne = boites[i].split(), [], ""
            for mot in mots:  # retour à la ligne simple dans la boîte
                if len(ligne) + len(mot) + 1 > 22:
                    lignes.append(ligne)
                    ligne = mot
                else:
                    ligne = f"{ligne} {mot}".strip()
            lignes.append(ligne)
            for j, texte in enumerate(lignes[:3]):
                d.add(String(x + l_boite / 2, y + h_boite - 11 - j * 10, texte, fontName=police, fontSize=8,
                             textAnchor="middle"))
            centres[i] = (x + l_boite / 2, y, y + h_boite)
    for de, vers, etiquette in liens:
        x1, bas1, _ = centres[de]
        x2, _, haut2 = centres[vers]
        d.add(Line(x1, bas1, x2, haut2 + 2, strokeColor=colors.black))
        d.add(Polygon([x2, haut2, x2 - 3, haut2 + 6, x2 + 3, haut2 + 6], fillColor=colors.black))
        if etiquette:
            d.add(String((x1 + x2) / 2 + 4, (bas1 + haut2) / 2, etiquette, fontName=police, fontSize=7))
    return d


def flux_page(page: dict, st: dict, police: str, premiere: bool, titre: str) -> list:
    """Transforme les blocs d'une page en éléments reportlab."""
    elements = [Paragraph(echapper(titre), st["titre_doc"])] if premiere else []
    for bloc in page["blocs"]:
        t = bloc["type"]
        if t == "titre":
            elements.append(Paragraph(echapper(bloc["texte"]), st["titre1" if bloc.get("niveau", 1) == 1 else "titre2"]))
        elif t == "paragraphe":
            elements.append(Paragraph(echapper(bloc["texte"]), st["texte"]))
        elif t == "liste":
            items = [ListItem(Paragraph(echapper(e), st["texte"]), leftIndent=12) for e in bloc["elements"]]
            elements.append(ListFlowable(items, bulletType="bullet", start="–", leftIndent=12))
        elif t == "tableau":
            if bloc.get("titre"):
                elements.append(Paragraph(echapper(bloc["titre"]), st["titre2"]))
            donnees = [[Paragraph(echapper(c), st["entete"]) for c in bloc["entetes"]]]
            donnees += [[Paragraph(echapper(str(c)), st["cellule"]) for c in ligne] for ligne in bloc["lignes"]]
            tableau = Table(donnees, repeatRows=1, hAlign="LEFT",
                            colWidths=[(LARGEUR - 2 * MARGE) / len(bloc["entetes"])] * len(bloc["entetes"]))
            tableau.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                                         ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                                         ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            elements += [tableau, Spacer(1, 6)]
        elif t == "figure":
            elements += [Spacer(1, 4), figure(bloc, police), Paragraph(echapper(bloc["legende"]), st["legende"])]
        elif t == "fiche":
            donnees = [[Paragraph(echapper(f"{nom} :"), st["entete"]), Paragraph(echapper(str(valeur)), st["cellule"])]
                       for nom, valeur in bloc["champs"]]
            tableau = Table(donnees, colWidths=[55 * mm, LARGEUR - 2 * MARGE - 55 * mm], hAlign="LEFT")
            tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                         ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.grey)]))
            elements.append(tableau)
        else:
            raise ValueError(f"type de bloc inconnu : {t}")
    return elements


def dessiner(doc: dict, scanne: bool) -> bytes:
    """Dessine le document page par page, et rend le PDF en mémoire."""
    police, gras = ("Mono", "Mono") if scanne else ("Sans", "Sans-Gras")
    st = styles(police, gras)
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    c.setTitle(doc["titre"])
    pages = doc["pages"]
    for n, page in enumerate(pages, start=1):
        # en-tête et pied de page
        c.setFont(police, 8)
        if scanne:
            c.drawString(MARGE, HAUTEUR - 12 * mm, "VALTÉRA INDUSTRIES — Archives techniques")
        elif doc["format"] == "Fiche de base de données":
            c.drawString(MARGE, HAUTEUR - 12 * mm, f"GMAO Atlas — export de la fiche {doc['reference_source']}")
        else:
            c.drawString(MARGE, HAUTEUR - 12 * mm, f"Valtéra Industries — {doc['type_document']}")
            c.drawRightString(LARGEUR - MARGE, HAUTEUR - 12 * mm, f"{doc['reference_source']} — {doc['version']}")
        c.drawString(MARGE, 10 * mm, f"{doc['reference_source']} — page {n}/{len(pages)}")
        titre = f"{doc['reference_source']} — {doc['titre']}"
        cadre = Frame(MARGE, 16 * mm, LARGEUR - 2 * MARGE, HAUTEUR - 34 * mm, showBoundary=0)
        contenu = KeepInFrame(cadre._aW, cadre._aH, flux_page(page, st, police, n == 1, titre), mode="shrink")
        cadre.addFromList([contenu], c)
        c.showPage()
    c.save()
    return tampon.getvalue()


def abimer(image: Image.Image, graine: int) -> Image.Image:
    """Donne à une page l'aspect d'un scan : gris, légère rotation, bruit, flou, compression JPEG."""
    hasard = random.Random(graine)
    image = image.convert("L").rotate(hasard.uniform(-1.2, 1.2), expand=False, fillcolor=255)
    pixels = image.load()
    largeur, hauteur = image.size
    for _ in range(largeur * hauteur // 60):  # poussières
        x, y = hasard.randrange(largeur), hasard.randrange(hauteur)
        pixels[x, y] = hasard.choice((0, 90, 160))
    image = image.filter(ImageFilter.GaussianBlur(0.7))
    image = image.point(lambda v: min(255, int(v * 0.92 + 12)))  # fond grisé, encre moins noire
    tampon = io.BytesIO()
    image.save(tampon, "JPEG", quality=55)
    return Image.open(tampon)


def scanner(pdf: bytes, graine: int) -> bytes:
    """Rend chaque page en image (150 dpi), l'abîme, et reconstruit un PDF d'images sans texte."""
    images = [abimer(page.render(scale=150 / 72).to_pil(), graine + i)
              for i, page in enumerate(pdfium.PdfDocument(pdf))]
    tampon = io.BytesIO()
    images[0].save(tampon, "PDF", resolution=150, save_all=True, append_images=images[1:])
    return tampon.getvalue()


def fabriquer(chemin_json: Path) -> Path:
    doc = json.loads(chemin_json.read_text(encoding="utf-8"))
    scanne = doc["format"] == "PDF scanné"
    pdf = dessiner(doc, scanne)
    if scanne:
        pdf = scanner(pdf, graine=sum(map(ord, doc["reference_source"])))
    nb = len(pdfium.PdfDocument(pdf))
    if nb != len(doc["pages"]):
        raise RuntimeError(f"{doc['reference_source']} : {nb} pages dans le PDF pour {len(doc['pages'])} dans le JSON")
    sortie = SOURCES / f"{doc['reference_source']}.pdf"
    sortie.write_bytes(pdf)
    return sortie


if __name__ == "__main__":
    SOURCES.mkdir(parents=True, exist_ok=True)
    fichiers = sorted(CONTENUS.glob("*.json")) if len(sys.argv) == 1 else [Path(a) for a in sys.argv[1:]]
    for f in fichiers:
        print(fabriquer(f).relative_to(ICI.parent.parent))
