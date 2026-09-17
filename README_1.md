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




## DESCRIPCION PROGRAMA

### INDEX
Descripción de la fase de indexado (para tu README)

El proyecto arranca con la fase de indexado: convertir el repositorio de vLLM en un índice que luego podamos consultar. La idea de fondo es sencilla. Si queremos responder preguntas sobre una base de código, primero tenemos que leer ese código, partirlo en trozos manejables y guardar esos trozos en un sitio fijo para que el buscador los pueda leer después. Eso es exactamente lo que hace el comando index.

Cuando ejecutas uv run python -m src index, el programa hace cuatro cosas, en este orden:

Buscar archivos. Recorre todo el árbol de data/raw/vllm-0.10.1 con rglob y se queda con los que terminan en .py o .md. Esas extensiones viven en supported_suffixes, un conjunto que se puede ampliar fácilmente: si algún día quieres indexar .txt o .rst, solo tienes que añadirlos ahí. Y para cualquier extensión nueva que no tenga estrategia propia, el Chunker usa un método genérico que corta cada max_chunk_size caracteres sin más, así que el sistema nunca se rompe por encontrarse un formato raro.
Leer los documentos. Carga el contenido de cada archivo en memoria y lo guarda en un diccionario {ruta: contenido}, con una barra de progreso de tqdm para que se vea que avanza.
Trocear. Aquí está el corazón de la fase. Cada documento se parte en trozos de como máximo max_chunk_size caracteres (por defecto 2000, el límite que pide el enunciado). Pero no se corta de cualquier manera: el Chunker elige la estrategia según la extensión del archivo. Para Markdown corta por párrafos, de forma que un párrafo nunca se parte por la mitad. Para Python corta en las líneas en blanco, que en la práctica suelen coincidir con los límites entre funciones y clases, de modo que cada trozo tiende a contener funciones completas. Y ojo a un detalle: los separadores no son solo el doble salto de línea, sino dos o más saltos (con espacios o tabuladores entre medias), porque en el repositorio real hay trozos con \n\n\n o más. Para eso usamos una expresión regular que busca \n(?:[ \t]*\n)+ y nos quedamos con el último separador que quepa en la ventana. Si no hay ningún separador antes del límite, se corta en el último salto de línea simple; y si ni eso hay, se corta justo en max_chunk_size. El resultado es una lista de trozos que cubren todo el documento sin huecos ni solapamientos.
Guardar el índice. Cada trozo se convierte en un objeto MinimalSource (ruta del archivo + índice de inicio + índice de fin) y se escribe todo en data/processed/index.json. Cada entrada tiene esta forma:
json
Copy
{
  "file_path": "data/raw/vllm-0.10.1/vllm/sampling_params.py",
  "first_character_index": 3571,
  "last_character_index": 5547,
  "text": "    n: int = 1\n    ..."
}
Try:
|
Las claves no son casuales: son exactamente las que espera el evaluador en los ficheros de resultados. En resumen:

Clave	Qué guarda
file_path	La ruta del archivo del que sale el trozo
first_character_index	La posición del primer carácter del trozo dentro del archivo
last_character_index	La posición del último carácter (exclusiva)
text	El contenido del trozo
Guardar el rango en vez de solo el texto es importante porque así podemos localizar el trozo original con precisión y, más adelante, recortar el contexto a lo que de verdad necesitamos.

Además, el comando mide los tiempos de cada fase y los muestra por pantalla: cuánto tarda en buscar, en leer, en trocear y en escribir el JSON, con el total en formato HH:MM:SS.microsegundos. Las tres fases pesadas (leer, trocear y crear el índice) llevan barra de progreso. Esto no es postureo: el enunciado exige que el indexado no tarde más de 5 minutos, y con los tiempos por fase puedes ver de un vistazo dónde se va el tiempo y demostrar que el programa es eficiente.

Sobre la validación: max_chunk_size se comprueba antes de hacer nada. Tiene que ser un entero positivo y no puede superar 2000. Si no lo es, el programa imprime un mensaje de error claro y termina con código de salida 1, sin tracebacks feos. La filosofía es que las clases de lógica (Index, Chunker) lanzan excepciones con raise cuando algo va mal, y la capa de CLI (la clase CLI, montada con Python Fire) las captura, imprime el error y sale limpiamente.

Los objetos que hemos creado y por qué:

Index: la clase que orquesta todo el proceso de indexado. Sabe dónde está el repositorio (data/raw/vllm-0.10.1), dónde se guarda el índice (data/processed) y qué extensiones soporta. Sus métodos son find_supported_files, read_file, load_documents, chunk_documents y save_index, cada uno con una responsabilidad única.
Chunker: la clase que decide cómo cortar. Tiene un diccionario de estrategias {extensión: método} y un método genérico de reserva. Así, añadir un formato nuevo es añadir una entrada al diccionario.
MinimalSource y el resto de modelos (UnansweredQuestion, AnsweredQuestion, RagDataset, MinimalSearchResults, MinimalAnswer, StudentSearchResults, StudentSearchResultsAndAnswer): modelos pydantic que definen la forma de los datos que van a circular por el sistema. MinimalSource es el que se usa en el indexado: un trozo de documento identificado por ruta y rango de caracteres. Los demás se usarán en las fases de búsqueda, respuesta y evaluación.
CLI: la interfaz de línea de comandos. Expone los comandos index, search, search_dataset, answer, answer_dataset y evaluate. De momento solo index está implementado; los demás son esqueletos que se irán rellenando en las siguientes fases.
Y un detalle de diseño que conviene recordar: el índice guarda los trozos con su texto, pero la fuente de verdad sigue siendo el archivo original. Si más adelante quieres cambiar el tamaño de los trozos, no hace falta tocar nada de la lógica: basta con volver a ejecutar index con otro max_chunk_size.


### SEARCH
### search_dataset
### answer
### answer_dataset
### evaluate

