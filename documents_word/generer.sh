#!/usr/bin/env bash
# Refait les versions Word des documents de méthode, à partir des fichiers Markdown du dépôt (qui font foi).
# À lancer depuis la racine du dépôt, après chaque modification de ces documents : ./documents_word/generer.sh
# Pandoc est pris par uv, sans rien installer.
set -euo pipefail
M=service-evaluation/documentation/methode_et_contrat
R=service-rag-exemple/documentation/reference
convertir() {   # $1 : le document Markdown ; $2 : le fichier Word à écrire
    uvx --from pypandoc-binary python -c "import pypandoc, sys; pypandoc.convert_file(sys.argv[1], 'docx', format='gfm', outputfile=sys.argv[2], extra_args=['--resource-path', sys.argv[3]])" \
        "$1" "documents_word/$2" "$(dirname "$1")"
    echo "documents_word/$2"
}
convertir "$M/methode_corpus_annote.md" RAG_1_Constituer_le_corpus_d_evaluation.docx
convertir "$R/techniques_rag.md"        RAG_2_Construire_le_pipeline.docx
convertir "$M/methode_evaluation.md"    RAG_3_Evaluer_le_RAG.docx
convertir "$M/contrat_des_fichiers.md"  CONTRAT.docx
convertir "$M/prompt_du_juge.md"        JUGE.docx
