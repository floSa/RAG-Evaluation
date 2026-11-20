# Format des contenus des documents sources

Chaque document du corpus d'exemple est décrit par un fichier JSON dans `corpus_exemple/fabrication/contenus/<reference_source>.json`. Le script de fabrication en tire le PDF de `corpus_exemple/sources/`. Le découpage en pages est écrit dans le JSON : la page d'un passage est donc connue exactement.

```json
{
  "reference_source": "PR-1101",
  "titre": "Consignation d'une armoire basse tension",
  "type_document": "Procédure",
  "source": "GED Valtéra",
  "version": "v3",
  "date": "2025-02-14",
  "format": "PDF natif",
  "criticite": "C2",
  "droits_acces": "Tous les utilisateurs",
  "en_vigueur": true,
  "remplace_par": null,
  "selection": "Tiré au hasard",
  "service": "Maintenance électrique",
  "site": "Deux sites",
  "pages": [
    {"blocs": [
      {"type": "titre", "niveau": 1, "texte": "1. Objet"},
      {"type": "paragraphe", "texte": "Cette procédure décrit…"},
      {"type": "liste", "elements": ["premier point", "second point"]},
      {"type": "tableau", "titre": "Tableau 1 — Matériel requis", "entetes": ["Matériel", "Quantité"], "lignes": [["VAT 1 000 V", "1"]]},
      {"type": "figure", "numero": 1, "legende": "Figure 1 — Schéma de principe de la consignation",
       "boites": [{"id": "a", "texte": "Arrivée TGBT"}, {"id": "b", "texte": "Interrupteur-sectionneur"}],
       "liens": [["a", "b", "câble 4x95 mm²"]]}
    ]}
  ]
}
```

Règles :

| Champ | Règle |
| --- | --- |
| `format` | `PDF natif`, `PDF scanné` ou `Fiche de base de données` |
| `criticite` | `C1`, `C2`, `C2 export`, `C3` |
| `droits_acces` | `Tous les utilisateurs`, `Maintenance` ou `Exploitation` |
| `selection` | `Tiré au hasard` ou `Choisi par le métier` |
| `pages` | une page tient sur une page A4 : 350 mots au plus, un tableau de 8 lignes au plus ; une figure prend une demi-page |
| `titre` (bloc) | niveau 1 ou 2, numéroté (« 2. », « 2.1 ») : il sert au chemin de titres du découpage |
| `figure` | 2 à 6 boîtes, reliées par des liens `[de, vers, étiquette]` ; la légende commence par « Figure N — » |
| Fiche de base | un seul bloc `{"type": "fiche", "champs": [["Numéro OT", "OT-24101"], ["Site", "Site A"], …]}` sur une page unique |

Style : français, sobre, technique, réaliste pour une entreprise industrielle. Chiffres toujours avec unités. Pas de caractères exotiques (pas d'émoji) ; les symboles « ° », « Ω », « ² », « ± », « € », « — » sont permis.
