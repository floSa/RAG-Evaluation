# Les comparaisons de configurations

Deux configurations du RAG, déjà évaluées sur le même corpus, comparées par `kit comparer`. Un dossier `<corpus>_<A>_contre_<B>/` par comparaison (A et B sans leur début commun, pour garder un chemin court), avec :

- **`RAPPORT.md`** : ce qui change de A à B, les écarts de scores et s'ils sont réels, les questions gagnées et perdues, la conclusion.
- `fichiers_techniques/comparaison.json` : tous les écarts.

Exemple rempli : [`service-evaluation-exemple/resultats/comparaisons_de_configurations/`](../../../service-evaluation-exemple/resultats/comparaisons_de_configurations/).
