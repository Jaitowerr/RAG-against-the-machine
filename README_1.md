El roadmap completo, paso a paso, de lo simple a lo complejo
Tu instinto de "hacer algo simple primero y luego especializar" es exactamente cómo hay que atacar este proyecto. Aquí tienes el orden real, dividido en fases pequeñas y verificables:

Fase 0 — Esqueleto que no rompe nada

src/__main__.py usa fire.Fire para exponer una clase con 6 métodos vacíos (index, search, search_dataset, answer, answer_dataset, evaluate), cada uno solo hace un print("index called") de momento.
✅ Verificas: uv run python -m src index te imprime el mensaje sin crashear.
Fase 1 — Leer archivos del corpus (sin indexar nada aún)
2. Escribes una función que recorra data/raw/vllm-0.10.1/ y liste todos los .py y .md que encuentra.

✅ Verificas: imprime cuántos archivos de cada tipo ha encontrado (algo como "1200 .py, 300 .md").
Fase 2 — Chunking (cortar en trozos) muy simple
3. Empiezas con un chunker "tonto": cortar cada archivo en bloques de máx. 2000 caracteres sin pensar en sintaxis (corte a lo bruto por posición). Esto ya te da algo funcional.

✅ Verificas: imprimes cuántos chunks salen y compruebas que ninguno supera 2000 caracteres.
Luego mejoras: un chunker para .py que corte por funciones/clases (usando el módulo ast de Python), y otro para .md que corte por encabezados #. Sustituyes el chunker tonto por estos dos.
Fase 3 — Los modelos Pydantic
5. Aquí sí defines MinimalSource, etc., porque ya tienes datos reales (los chunks) que necesitas guardar con esa forma.

Fase 4 — Indexación léxica (BM25 o TF-IDF)
6. Con los chunks ya creados, construyes el índice (por ejemplo con la librería rank-bm25), y lo guardas en disco en data/processed/ (por ejemplo con pickle o json).

✅ Verificas: el comando index termina y aparece un archivo dentro de data/processed/.
Fase 5 — Búsqueda (search)
7. Cargas el índice guardado, recibes una pregunta por CLI, calculas el score BM25/TF-IDF contra todos los chunks, devuelves el top-k.

✅ Verificas: uv run python -m src search "algo" --k 5 imprime 5 resultados con su file_path y rango de caracteres.
Repites lo mismo pero leyendo un dataset JSON completo en vez de una sola pregunta (search_dataset), guardando el resultado como StudentSearchResults.
Fase 6 — Evaluación local (sin moulinette todavía)
9. Implementas tu propio evaluate sencillo para comparar tus resultados contra el dataset de respuestas y sacar un recall@k aproximado, para iterar rápido sin depender del binario.

Fase 7 — Generación con Qwen3-0.6B
10. Cargas el modelo (con transformers), montas un prompt simple: "Contexto: [chunks encontrados]. Pregunta: [pregunta]. Responde basándote solo en el contexto."
11. Primero pruébalo con una pregunta fija hardcodeada para ver que el modelo responde algo coherente.
12. Luego conectas esto al comando answer y después a answer_dataset (procesa todo un JSON).

Fase 8 — Pulido y cumplimiento estricto del subject
13. Manejo de errores (queries vacías, JSON mal formado, archivos que faltan) sin que crashee.
14. tqdm en los bucles largos.
15. Pasar make lint y make lint-strict sin errores.
16. Comprobar tiempos (indexado <5 min, 200 preguntas <90 seg).
17. Rellenar el README.md con las secciones obligatorias.

Fase 9 — Bonus (solo si todo lo anterior está 100% validado)
18. Aquí sí, según el subject: no van en carpeta aparte, se integran en el mismo src/ (por ejemplo añadiendo un módulo de embeddings que tu search puede usar opcionalmente, o un flag --hybrid en tus comandos). El subject solo dice que "cada bonus cuenta si está implementado y funcionando", no exige aislamiento en carpetas.




| Comando | Qué hace | Cuándo lo usa el cliente | Parámetros y su función |
|---|---|---|---|
| `index` | Lee todo el código fuente de `data/raw/`, lo trocea (chunking) y construye el índice de búsqueda, guardándolo en `data/processed/`. | Siempre primero. Sin índice no hay nada que buscar. Se ejecuta una vez (o cada vez que cambien los datos fuente). | `max_chunk_size`: número máximo de caracteres por fragmento. Controla la granularidad del índice: fragmentos más pequeños = más precisión pero menos contexto; fragmentos más grandes = más contexto pero menos precisión. |
| `search` | Encuentra los k fragmentos de código más relevantes para una única pregunta escrita al momento. Solo imprime resultados, no genera una respuesta en lenguaje natural. | Cuando el cliente quiere probar rápidamente el motor de búsqueda con una pregunta interactiva. | `query`: la pregunta/texto de búsqueda. `k`: cuántos fragmentos devolver (top-k). |
| `search_dataset` | Igual que `search`, pero en lugar de una pregunta lee un archivo JSON con muchas preguntas (dataset) y ejecuta la búsqueda para cada una, guardando todos los resultados en un JSON de salida (`StudentSearchResults`). | Cuando el cliente quiere evaluar el motor de búsqueda contra un dataset completo de una vez, no pregunta por pregunta. | `dataset_path`: ruta al JSON de entrada con las preguntas. `k`: top-k a recuperar por pregunta. `save_directory`: carpeta donde se guardará el JSON de resultados generado. |
| `answer` | Como `search`, pero además genera una respuesta en lenguaje natural (usando los fragmentos recuperados como contexto) para una única pregunta. | Cuando el cliente quiere probar el sistema RAG completo (retrieval + generación) con una pregunta interactiva. | `query`: la pregunta. `k`: cuántos fragmentos usar como contexto para generar la respuesta. |
| `answer_dataset` | Toma un JSON que ya contiene resultados de búsqueda (la salida de `search_dataset`) y genera una respuesta para cada pregunta, guardando todo en un nuevo JSON (`StudentSearchResultsAndAnswer`). | Cuando el cliente ya ejecutó `search_dataset` y ahora quiere generar respuestas en bloque a partir de esos resultados, sin rehacer la búsqueda. | `student_search_results_path`: ruta al JSON producido por `search_dataset` (búsquedas ya hechas). `save_directory`: carpeta donde se guardará el JSON final con las respuestas. |
| `evaluate` | Compara los resultados de búsqueda del estudiante contra un dataset de referencia (con respuestas/fuentes correctas conocidas) y calcula una métrica, recall@k, para medir cómo de bueno es el motor de búsqueda. | Al final, para medir objetivamente la calidad del sistema construido, comparándolo contra el "ground truth". | `student_search_results_path`: JSON con los resultados generados por el estudiante (de `search_dataset`). `dataset_path`: JSON con las respuestas/fuentes de referencia correctas. |

## Flujo de uso típico
index → search_dataset → answer_dataset → evaluate
(una vez) (búsqueda masiva) (respuestas masivas) (medir calidad)


En paralelo, `search` y `answer` se usan para pruebas manuales rápidas y puntuales.



### Note on flag syntax

Python Fire does not enforce a fixed number of dashes for named flags.
`-k 3`, `--k 3` and even `---k 3` are all interpreted identically as the
`k` argument. This is a Fire library behavior, not a project limitation,
and does not affect input validation: whatever value reaches the CLI
methods is validated the same way regardless of how many dashes were used.