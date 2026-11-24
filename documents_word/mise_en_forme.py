"""Met en forme un document Word fabriqué par pandoc : titres colorés, tableaux avec bordures,
en-tête de tableau coloré, lignes alternées, largeurs de colonnes selon le contenu.

Usage : python mise_en_forme.py <fichier.docx>   (le fichier est réécrit sur place)
Lancé par generer.sh, après la conversion du Markdown en Word.
"""
import sys

import docx
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

MARINE = RGBColor(0x0B, 0x2A, 0x6F)      # titres, en-têtes de tableau
ORANGE = "FF8A1F"                         # filet sous les titres de niveau 1
BORDURE = "9AA8C7"                        # bordures des tableaux
ENTETE = "0B2A6F"                         # fond de l'en-tête des tableaux
LIGNE_PAIRE = "EEF2FA"                    # fond d'une ligne sur deux
LARGEUR_UTILE_CM = 17.0                   # A4 (21 cm) moins deux marges de 2 cm
POLICE = "Calibri"


# Ordre des éléments imposé par le schéma Word : un élément mal placé fait dire à Word que le fichier est illisible.
ORDRE_TBLPR = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize", "tblW", "jc",
               "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook", "tblCaption", "tblDescription"]
ORDRE_PPR = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr", "suppressLineNumbers",
             "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct", "topLinePunct", "autoSpaceDE",
             "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents",
             "suppressOverlap", "jc", "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle",
             "rPr", "sectPr", "pPrChange"]
ORDRE_TCPR = ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar", "textDirection",
              "tcFitText", "vAlign", "hideMark"]


def inserer(parent, enfant, ordre):
    """Ajoute `enfant` dans `parent`, avant le premier élément qui doit le suivre dans l'ordre du schéma."""
    nom = enfant.tag.split("}")[1]
    for ancien in parent.findall(enfant.tag):
        parent.remove(ancien)
    suivants = ordre[ordre.index(nom) + 1:]
    for existant in parent:
        if existant.tag.split("}")[1] in suivants:
            existant.addprevious(enfant)
            return
    parent.append(enfant)


def poser_police(style, taille, gras=None, couleur=None):
    style.font.name = POLICE
    style.font.size = Pt(taille)
    if gras is not None:
        style.font.bold = gras
    if couleur is not None:
        style.font.color.rgb = couleur
    # la police doit aussi être posée pour les caractères « asiatiques » et « complexes », sinon Word garde l'ancienne
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attribut in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attribut), POLICE)
    for attribut in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        fonts.attrib.pop(qn(attribut), None)


def mettre_en_forme_styles(document):
    styles = document.styles
    for nom in ("Normal", "Body Text", "First Paragraph", "Compact"):
        poser_police(styles[nom], 10.5)
    for nom in ("Body Text", "First Paragraph"):
        pf = styles[nom].paragraph_format
        pf.space_before, pf.space_after = Pt(0), Pt(7)
        pf.line_spacing_rule, pf.line_spacing = WD_LINE_SPACING.MULTIPLE, 1.15
    styles["Compact"].paragraph_format.space_after = Pt(2)
    poser_police(styles["Title"], 26, True, MARINE)
    tailles = {"Heading 1": 18, "Heading 2": 14, "Heading 3": 12}
    for nom, taille in tailles.items():
        poser_police(styles[nom], taille, True, MARINE)
        pf = styles[nom].paragraph_format
        pf.space_before, pf.space_after, pf.keep_with_next = Pt(18 if nom == "Heading 1" else 12), Pt(6), True
    # filet orange sous les titres de niveau 1
    ppr = styles["Heading 1"].element.get_or_add_pPr()
    bordure = OxmlElement("w:pBdr")
    bas = OxmlElement("w:bottom")
    for cle, valeur in (("val", "single"), ("sz", "12"), ("space", "2"), ("color", ORANGE)):
        bas.set(qn(f"w:{cle}"), valeur)
    bordure.append(bas)
    inserer(ppr, bordure, ORDRE_PPR)


def mettre_en_forme_encadres(document):
    """Les citations (« > À retenir ») deviennent des encadrés : filet orange à gauche, fond clair."""
    style = document.styles["Block Text"]
    poser_police(style, 10.5)
    ppr = style.element.get_or_add_pPr()
    bordure = OxmlElement("w:pBdr")
    gauche = OxmlElement("w:left")
    for cle, valeur in (("val", "single"), ("sz", "24"), ("space", "8"), ("color", ORANGE)):
        gauche.set(qn(f"w:{cle}"), valeur)
    bordure.append(gauche)
    inserer(ppr, bordure, ORDRE_PPR)
    fond_encadre = OxmlElement("w:shd")
    for cle, valeur in (("val", "clear"), ("color", "auto"), ("fill", "FFF3E6")):
        fond_encadre.set(qn(f"w:{cle}"), valeur)
    inserer(ppr, fond_encadre, ORDRE_PPR)
    style.paragraph_format.left_indent = Cm(0.5)
    style.paragraph_format.space_before = style.paragraph_format.space_after = Pt(8)


def poser_marges(document):
    for section in document.sections:
        section.page_width, section.page_height = Cm(21), Cm(29.7)
        section.left_margin = section.right_margin = Cm(2)
        section.top_margin = section.bottom_margin = Cm(2)


def fond(cellule, couleur):
    tcpr = cellule._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), couleur)
    inserer(tcpr, shd, ORDRE_TCPR)


def largeurs_colonnes(table):
    """Largeur de chaque colonne en cm : proportionnelle au contenu, mais jamais plus étroite que son mot le plus long."""
    n = len(table.columns)
    poids, plancher = [], []
    for j in range(n):
        textes = [ligne.cells[j].text for ligne in table.rows if j < len(ligne.cells)]
        moyenne = sum(len(t) for t in textes) / max(len(textes), 1)
        poids.append(min(max(moyenne, 14), 70))
        mot_le_plus_long = max((len(mot) for t in textes for mot in t.split()), default=1)
        plancher.append(min(mot_le_plus_long * 0.19 + 0.5, 6.0))   # ~0,19 cm par caractère à 9,5 pt
    total = sum(poids)
    largeurs = [max(LARGEUR_UTILE_CM * p / total, f) for p, f in zip(poids, plancher)]
    exces = sum(largeurs) - LARGEUR_UTILE_CM
    if exces > 0:                       # on reprend l'excédent sur les colonnes qui ont de la marge au-dessus de leur plancher
        marge = [l - f for l, f in zip(largeurs, plancher)]
        total_marge = sum(marge)
        if total_marge > 0:
            largeurs = [l - exces * m / total_marge for l, m in zip(largeurs, marge)]
    return largeurs


def mettre_en_forme_tableau(table):
    tbl = table._tbl
    tblpr = tbl.tblPr
    bordures = OxmlElement("w:tblBorders")
    for cote in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{cote}")
        for cle, valeur in (("val", "single"), ("sz", "4"), ("space", "0"), ("color", BORDURE)):
            b.set(qn(f"w:{cle}"), valeur)
        bordures.append(b)
    inserer(tblpr, bordures, ORDRE_TBLPR)
    marges = OxmlElement("w:tblCellMar")
    for cote, valeur in (("top", "50"), ("left", "90"), ("bottom", "50"), ("right", "90")):
        m = OxmlElement(f"w:{cote}")
        m.set(qn("w:w"), valeur)
        m.set(qn("w:type"), "dxa")
        marges.append(m)
    inserer(tblpr, marges, ORDRE_TBLPR)
    mise_en_page = OxmlElement("w:tblLayout")
    mise_en_page.set(qn("w:type"), "fixed")
    inserer(tblpr, mise_en_page, ORDRE_TBLPR)

    largeurs = largeurs_colonnes(table)
    grille = tbl.tblGrid
    for colonne, largeur in zip(grille.findall(qn("w:gridCol")), largeurs):
        colonne.set(qn("w:w"), str(int(largeur * 567)))   # 1 cm = 567 twips
    tblw = tblpr.find(qn("w:tblW"))
    if tblw is None:
        tblw = OxmlElement("w:tblW")
        inserer(tblpr, tblw, ORDRE_TBLPR)
    tblw.set(qn("w:type"), "dxa")
    tblw.set(qn("w:w"), str(int(sum(largeurs) * 567)))

    for i, ligne in enumerate(table.rows):
        if i == 0:                                      # en-tête répété en haut de chaque page
            trpr = ligne._tr.get_or_add_trPr()
            trpr.append(OxmlElement("w:tblHeader"))
        # une ligne ne se coupe pas entre deux pages
        ligne._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for j, cellule in enumerate(ligne.cells):
            if j < len(largeurs):
                cellule.width = Cm(largeurs[j])
            if i == 0:
                fond(cellule, ENTETE)
            elif i % 2 == 0:
                fond(cellule, LIGNE_PAIRE)
            for paragraphe in cellule.paragraphs:
                paragraphe.paragraph_format.space_after = Pt(1)
                for run in paragraphe.runs:
                    run.font.size = Pt(9.5)
                    if i == 0:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)


def mettre_a_l_echelle_images(document):
    """Une image ne dépasse jamais la largeur utile de la page."""
    largeur_max = Cm(LARGEUR_UTILE_CM)
    for forme in document.inline_shapes:
        if forme.width > largeur_max:
            rapport = largeur_max / forme.width
            forme.width, forme.height = int(forme.width * rapport), int(forme.height * rapport)


def main(chemin):
    document = docx.Document(chemin)
    poser_marges(document)
    mettre_en_forme_styles(document)
    mettre_en_forme_encadres(document)
    for table in document.tables:
        mettre_en_forme_tableau(table)
    mettre_a_l_echelle_images(document)
    document.save(chemin)


if __name__ == "__main__":
    main(sys.argv[1])
