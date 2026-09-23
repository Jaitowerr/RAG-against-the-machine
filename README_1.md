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
### SEARCH

Con el índice ya en disco, toca la fase de búsqueda: convertir una pregunta en una lista ordenada de los trozos más relevantes del corpus. La idea de fondo es sencilla. La pregunta y los trozos hablan el mismo idioma (palabras en minúsculas), así que basta con puntuar cada trozo contra la pregunta con una fórmula léxica (BM25), ordenar y devolver el top-k. Y en el mismo formato que produce el indexado: `search` devuelve objetos `MinimalSource`, exactamente lo mismo que `index` guarda en `index.json`, de modo que las dos fases hablan el mismo idioma.

Cuando ejecutas `uv run python -m src search "How to configure the OpenAI server?" --k 5`, el programa hace seis cosas, en este orden:

**Validar la entrada.** Antes de tocar nada se comprueba que `query` no esté vacía (ni llena de espacios, que para el caso es lo mismo) y que `k` sea un entero estrictamente positivo. Si algo falla: mensaje claro por stderr y código de salida 1, sin tracebacks.

**Cargar el índice.** `load_index` lee `data/processed/index.json` y comprueba que el archivo exista, que sea JSON válido, que sea una lista y que no esté vacía. Cualquier cosa rara se convierte en un `ValueError` con mensaje claro.

**Tokenizar.** La pregunta y los 12.370 trozos pasan por la misma función: minúsculas y `re.findall(r"[a-z0-9]+", ...)`, que se queda con las secuencias de letras y números y descarta puntuación y símbolos. Usar la misma regla en los dos lados es lo que hace que `OpenAI?` en la pregunta encuentre `openai` en el texto. El corpus entero se tokeniza en una sola pasada con barra de progreso (~0.3 s).

**Contar términos.** De la tokenización salen las dos estructuras que alimentan el scoring. `term_freqs` es un `Counter` por trozo: cuántas veces aparece cada palabra dentro de ese trozo. `doc_freq` es en cuántos trozos aparece cada palabra. Ojo al matiz: doc_freq no es frecuencia total. Una palabra puede aparecer 4.703 veces en el corpus, pero si es toda en 3 trozos, su doc_freq es 3. De ahí sale el efecto "las palabras raras valen más".

**Puntuar con BM25.** Cada trozo recibe su score con `k1 = 1.2` y `b = 0.75`:

```
IDF(t) = ln( (N - df + 0.5) / (df + 0.5) + 1 )

score(query, d) = Σ IDF(t) · tf · (k1 + 1) / ( tf + k1 · (1 - b + b · |d| / avgdl) )
```

donde `N` es el número total de trozos, `df` el doc_freq del término, `tf` cuántas veces aparece en el trozo, `|d|` su longitud en tokens y `avgdl` la media. Dos detalles cómodos: un `Counter` devuelve 0 si la palabra no está (nada de KeyError ni comprobaciones extra), y los términos con tf = 0 se saltan directamente. Y como el log lleva un `+1` dentro, el IDF es siempre positivo: va desde 0.48 para `the` (está en casi todos los trozos) hasta 10.12 para una palabra que no existe ni una vez.

**Ordenar y devolver.** Se ordenan todos los trozos por score de mayor a menor y se queda el top-k. El sort de Python es estable, así que los empates (por ejemplo trozos con score 0.0 porque no comparten ni una palabra con la pregunta) conservan el orden del índice: la salida es determinista, nunca aleatoria. El top-k se convierte en `MinimalSource` y la CLI lo imprime numerado con su rango `[first_character_index:last_character_index]`, más el tiempo total en `HH:MM:SS.microsegundos`.

**Por qué BM25 y no TF-IDF.** El enunciado permite cualquiera de los dos. TF-IDF multiplica el tf a secas: una palabra repetida 30 veces puntúa 30 veces más, y los trozos largos ganan solo por ser largos. BM25 corrige las dos cosas: la saturación de tf hace que repetir una palabra rinda cada vez menos, y la normalización de longitud (el término con `b`) penaliza o premia según el trozo se aleje de la media. Con trozos de tamaños muy distintos —los nuestros van de unas pocas líneas a 2.000 caracteres— eso se nota. `k1 = 1.2` y `b = 0.75` son los valores estándar de la literatura.

**El detalle de rendimiento que lo cambió todo.** La primera versión llamaba a `_average_chunk_length()` dentro de `_score_chunk`. Suena inocente, pero `_score_chunk` se ejecuta 12.370 veces por búsqueda, y cada llamada volvía a sumar las longitudes de los 12.370 trozos: coste cuadrático, unos 5.5 s por query. La solución es de libro: la media no cambia durante la búsqueda, así que se calcula una sola vez en `prepare()` y se guarda en `self.average_chunk_length`. Resultado: de ~5.5 s a ~0.6 s por búsqueda, con resultados idénticos.

**Sobre la validación.** Misma filosofía que en el indexado: las clases de lógica lanzan excepciones (`raise ValueError`) y la capa de CLI las captura, imprime el error y sale con código 1. Lo degenerado que ya está cubierto: índice inexistente, malformado (un JSON que no es lista) o vacío; query vacía o de espacios; `k` igual a 0, negativo, no numérico, booleano o decimal (`2.5`). Dos perlas de Python que obligaron a checks específicos: `isinstance(True, int)` es `True` (por eso un bool se rechaza antes de convertir), e `int(2.5)` trunca sin quejarse (por eso un float con decimales se rechaza antes del `int()`). Los errores de sintaxis del propio CLI (flags mal escritas, comandos que no existen) los captura Python Fire antes de llegar a nuestro código, con su usage y un código de salida distinto de cero: también falla limpio.

Los objetos que hemos creado y por qué:

**Search**: la clase que orquesta la búsqueda. Guarda todo lo que necesita para puntuar y nada más:

Atributo	Qué guarda
entries	Los chunks tal cual los escribió index (con su text)
tokens	Los 12.370 chunks tokenizados, una lista de listas
term_freqs	Un Counter por chunk: frecuencia de cada palabra dentro del chunk
doc_freq	En cuántos chunks aparece cada palabra
query_tokens	La pregunta tokenizada
average_chunk_length	Media de tokens por chunk, pr


prepare() enciende todo en orden (cargar, tokenizar query, tokenizar corpus, contar términos, media) y es lo único que hay que llamar antes de buscar. _idf, _score_chunk y _count_matching_terms son las piezas internas del scoring, con guion bajo; lo único público es prepare() y search().

MinimalSource: no hay que crear nada nuevo. search devuelve exactamente lo mismo que el indexado guarda, así que los resultados de búsqueda se pueden serializar, comparar y reutilizar sin conversiones raras.

CLI.search: la capa fina. Valida la entrada, cronometra la operación completa e imprime los resultados numerados. Nada de lógica de scoring aquí: si un día cambiamos BM25 por otra cosa, la CLI no se entera.

Y un detalle de diseño que conviene recordar: search() acepta un parámetro query opcional; si no se pasa, usa el de la instancia. Parece azúcar, pero es la puerta a search_dataset: preparar el índice una vez y lanzar las preguntas encima, en vez de pagar la carga y tokenización del corpus (~0.6 s) por cada pregunta. Con 200 preguntas y un límite de 90 segundos, pagar la preparación una sola vez no es una optimización, es la diferencia entre cumplir el enunciado y no cumplirlo. Igual que en el indexado, search nunca abre los archivos originales: toda su visión del mundo le viene del index.json, así que si reindexas con otro max_chunk_size, la búsqueda se adapta sola.






### search_dataset

### SEARCH_DATASET

Con el buscador funcionando pregunta a pregunta, toca el salto de escala: pasar de una pregunta interactiva a un dataset completo de una tacada. La idea de fondo es sencilla. El evaluador no va a escribir preguntas a mano: va a lanzar un JSON con decenas de preguntas contra nuestro motor y a medir cuántas fuentes acertamos. `search_dataset` es exactamente eso: el mismo motor BM25 de `search`, pero leyendo las preguntas de un archivo y guardando todos los resultados en un único JSON con la forma que espera el moulinette (`StudentSearchResults`).

Cuando ejecutas `uv run python -m src search_dataset data/datasets/UnansweredQuestions/dataset_code_public.json --k 10`, el programa hace cinco cosas, en este orden:

**Validar la entrada.** Antes de tocar nada se comprueba que `dataset_path` exista, sea fichero, sea `.json` y se pueda leer; que `k` sea un entero estrictamente positivo; y que `save_directory` sea una carpeta válida (`data/output` por defecto). Aquí está el guard más importante del comando: la carpeta de salida **no puede ser la misma que la del dataset de entrada**. El motivo es que el fichero de salida se llama igual que el de entrada, así que si las carpetas coincidieran, el resultado pisaría al dataset original. La comparación se hace con `.resolve()`, que convierte ambas rutas a absolutas canónicas: `data/output`, `./data/output` y `data/datasets/UnansweredQuestions/../output` son la misma carpeta para `Path` pero distintas como strings, y solo `resolve()` las iguala. Además el guard corre antes del `mkdir`: si la carpeta es la del dataset, el programa aborta sin crear ni escribir absolutamente nada.

**Cargar el dataset.** `load_dataset` lee el JSON y comprueba que sea un objeto con la clave `rag_questions`, que sea una lista no vacía y que cada pregunta sea un objeto con `question_id` y un texto no vacío. Los errores llevan la posición: `Dataset question 42 has no 'question_id'`. Cualquier cosa rara (fichero ilegible, JSON roto, lista vacía) se convierte en un `ValueError` con mensaje claro.

**Preparar el índice una sola vez.** `search_all` llama a `prepare()` antes del bucle: cargar el `index.json`, tokenizar los 12.370 trozos (~0.3 s), contar `term_freqs`, `doc_freq` y la longitud media. Toda esa preparación se paga una vez, no una por pregunta. Este es el detalle que separa el cumplimiento del enunciado de no cumplirlo: el límite son 200 preguntas en 90 segundos, y pagar la preparación dentro del bucle serían 200 × 0.6 s solo en encender.

**Buscar cada pregunta.** El bucle de `tqdm` recorre las preguntas y para cada una llama a `self.search(query)`: el mismo BM25 de la fase anterior, sin una línea de scoring duplicada. Cada resultado se envuelve en un `MinimalSearchResults` (`question_id`, `question`, `retrieved_sources`), donde las fuentes recuperadas son `MinimalSource` de las de toda la vida: las mismas que produce `search` y guarda `index`. Las tres fases hablan el mismo idioma.

**Guardar.** Todo se envuelve en un `StudentSearchResults` (la lista de resultados más el `k` usado, para que el JSON cuente por sí mismo cómo se generó) y se escribe con `model_dump_json(indent=2)` en `save_directory / dataset_path.name`: mismo nombre que el fichero de entrada, distinta carpeta. Con el default, `data/output/dataset_code_public.json`. La forma de cada entrada:

    {
      "search_results": [
        {
          "question_id": "189c8b8a-...",
          "question": "What activation formats does ...?",
          "retrieved_sources": [
            {
              "file_path": "data/raw/vllm-0.10.1/docs/design/fused_moe_modular_kernel.md",
              "first_character_index": 16953,
              "last_character_index": 18260
            }
          ]
        }
      ],
      "k": 10
    }

**Sobre la validación.** Misma filosofía que en las dos fases anteriores: las clases de lógica lanzan excepciones (`raise ValueError`) y la capa de CLI las captura, imprime el error por `stderr` y sale con código 1. Lo degenerado que ya está cubierto: dataset inexistente, ilegible, malformado, sin preguntas o con preguntas sin `question_id` o vacías; `save_directory` que es un fichero, tiene extensión, no se puede crear o coincide con la carpeta del dataset de entrada; y `k` igual a 0, negativo, no numérico, booleano o decimal. El orden importa y no es casual: primero se valida el fichero de entrada (así su `.parent` existe y `resolve()` es seguro), luego `k`, y al final la carpeta de salida. Y se nota en la práctica: en la ejecución de prueba con la carpeta prohibida, el error aparece antes del `-> Cargadas 99 preguntas`, o sea, sin cargar índice, sin tokenizar y sin escribir.

Los objetos que hemos creado y por qué:

Objeto	Qué es y por qué
SearchDataset	La clase que orquesta el comando. Es subclase de Search: hereda todo el motor BM25 (prepare, search, _idf, _score_chunk...) y añade solo sus tres responsabilidades nuevas: load_dataset, search_all y save_results. Se construye con query="" porque cada pregunta la sobrescribe al vuelo.
MinimalSearchResults	El resultado por pregunta: question_id, question y retrieved_sources. No hizo falta crear ningún tipo nuevo para las fuentes: son las mismas que produce search y guarda index.
StudentSearchResults	El envoltorio de salida que espera el evaluador: la lista de resultados más el k empleado.
CLI.search_dataset	La capa fina: valida, cronometra e imprime. Toda la lógica vive en SearchDataset; si un día cambia el motor, la CLI no se entera.

Con datos reales: 99 preguntas en ~3.5 s de reloj total, de los que menos de un segundo son preparación y ~0.03 s por pregunta (unas 33 preguntas/segundo). El límite del enunciado es 200 preguntas en 90 s: hay margen de sobra.

Y un detalle de diseño que conviene recordar: SearchDataset no copia nada de Search, lo hereda. Si un día cambiamos BM25, afinamos el tokenizer o añadimos un bonus de embeddings, search_dataset mejora gratis junto a search. Y la regla del nombre de salida —mismo nombre que el fichero de entrada, distinta carpeta, jamás la misma— cierra el comando: la salida de search_dataset es siempre reconocible, y el dataset original es intocable por construcción.



### answer
### answer_dataset


### EVALUATE

La fase `evaluate` sirve para medir la calidad del buscador. No evalúa todavía si la respuesta generada por la IA está bien redactada, sino si el sistema ha recuperado las fuentes correctas.

El comando compara dos archivos:

1. El JSON generado por `search_dataset`.
2. El dataset de referencia, que contiene las fuentes correctas para cada pregunta.

El flujo principal es:

```text
index → search_dataset → evaluate
```

index crea el índice, search_dataset busca las fuentes relevantes y evaluate compara los resultados recuperados con las fuentes correctas.

Uso
bash
Copy
make run -- evaluate \
  --student_search_results_path data/output/dataset_code_public.json \
  --dataset_path data/datasets/AnsweredQuestions/dataset_code_public.json
Try:
|
El argumento student_search_results_path indica la ruta del JSON generado por search_dataset.

El argumento dataset_path indica la ruta del dataset de referencia con las fuentes correctas.

Funcionamiento de Evaluate
La lógica de evaluación está implementada en la clase Evaluate, dentro de evaluate.py.

El método principal es:

python
Copy
start_program()
Try:
|
Este método ejecuta todos los pasos de la evaluación en orden:

python
Copy
def start_program(self) -> None:
    self.load_results()
    self.load_dataset()
    self.validate_question_ids()
    self.compare_sources()
    self.calculate_recall_at_k()
Try:
|
Cada método tiene una responsabilidad concreta.

1. Cargar los resultados del estudiante
El método load_results() lee el archivo JSON generado por search_dataset.

python
Copy
def load_results(self) -> None:
    data = self._load_json(self.student_search_results_path)
    self.student_results = StudentSearchResults.model_validate(data)
Try:
|
Primero se lee el archivo mediante _load_json().

Después, el contenido se valida con el modelo Pydantic StudentSearchResults.

El archivo contiene:

Los resultados de búsqueda de cada pregunta.
El question_id de cada pregunta.
La pregunta.
Las fuentes recuperadas.
El valor de k utilizado.
Una estructura simplificada del archivo es:

json
Copy
{
  "search_results": [
    {
      "question_id": "id-de-la-pregunta",
      "question": "Pregunta del dataset",
      "retrieved_sources": [
        {
          "file_path": "ruta/al/archivo.py",
          "first_character_index": 100,
          "last_character_index": 500
        }
      ]
    }
  ],
  "k": 5
}
Try:
|
El valor de k indica cuántas fuentes se solicitaron para cada pregunta durante la búsqueda.

2. Cargar el dataset de referencia
El método load_dataset() lee el archivo que contiene las respuestas correctas.

python
Copy
def load_dataset(self) -> None:
    data = self._load_json(self.dataset_path)
    self.dataset = RagDataset.model_validate(data)
Try:
|
El contenido se valida mediante el modelo Pydantic RagDataset.

El dataset de referencia contiene las preguntas y sus fuentes correctas. Estas fuentes representan el ground truth, es decir, la información contra la que se comparan los resultados del estudiante.

Una pregunta puede tener una o varias fuentes correctas:

json
Copy
{
  "question_id": "id-de-la-pregunta",
  "question": "Pregunta del dataset",
  "sources": [
    {
      "file_path": "ruta/al/archivo.py",
      "first_character_index": 100,
      "last_character_index": 500
    }
  ]
}
Try:
|
3. Validar los identificadores de las preguntas
El método validate_question_ids() comprueba que todas las preguntas del dataset de referencia que tienen fuentes dispongan también de un resultado en el archivo del estudiante.

Primero recoge los identificadores de las preguntas recuperadas:

python
Copy
student_ids = {
    result.question_id
    for result in self.student_results.search_results
}
Try:
|
Después recoge los identificadores de las preguntas del dataset que tienen fuentes:

python
Copy
dataset_ids = {
    question.question_id
    for question in self.dataset.rag_questions
    if hasattr(question, "sources")
}
Try:
|
A continuación calcula qué identificadores del dataset no aparecen en los resultados del estudiante:

python
Copy
missing_ids = dataset_ids - student_ids
Try:
|
Si falta alguno, se lanza un error:

python
Copy
raise ValueError(
    "Some dataset questions are missing from student results."
)
Try:
|
Esta comprobación evita evaluar un conjunto incompleto de preguntas.

4. Comparar las fuentes
El método compare_sources() calcula el recall individual de cada pregunta.

Primero organiza los resultados del estudiante por question_id:

python
Copy
student_by_id = {
    result.question_id: result
    for result in self.student_results.search_results
}
Try:
|
Esto permite localizar rápidamente los resultados correspondientes a cada pregunta del dataset.

Después, para cada pregunta:

Obtiene las fuentes correctas.
Obtiene las fuentes recuperadas por el estudiante.
Comprueba qué fuentes correctas han sido encontradas.
Calcula el recall de esa pregunta.
La parte principal es:

python
Copy
found_sources = sum(
    self._is_found(retrieved_sources, source)
    for source in correct_sources
)
Try:
|
Por cada fuente correcta se llama a _is_found().

El resultado de cada pregunta se guarda en:

python
Copy
self.question_recalls[question.question_id]
Try:
|
5. Cuándo se considera encontrada una fuente
Una fuente recuperada se considera válida cuando se cumplen dos condiciones:

Pertenece al mismo archivo.
Su rango de caracteres tiene suficiente solapamiento con el rango correcto.
La comparación del archivo es exacta:

python
Copy
if source.file_path != true_source.file_path:
    continue
Try:
|
Si las rutas son diferentes, esa fuente no cuenta.

Después se calcula el solapamiento entre los dos rangos mediante IoU.

6. Cálculo del IoU
IoU significa Intersection over Union, es decir, intersección sobre unión.

Se utiliza para comparar dos rangos de caracteres.

El método es:

python
Copy
@staticmethod
def _iou(
    first_a: int,
    last_a: int,
    first_b: int,
    last_b: int,
) -> float:
Try:
|
La intersección se calcula así:

python
Copy
intersection = min(last_a, last_b) - max(first_a, first_b)
Try:
|
Si los rangos no se solapan, la intersección es cero:

python
Copy
if intersection <= 0:
    return 0.0
Try:
|
La unión se calcula mediante el rango total cubierto por ambos intervalos:

python
Copy
union = max(last_a, last_b) - min(first_a, first_b)
Try:
|
Finalmente:

python
Copy
return intersection / union
Try:
|
La fórmula matemática es:

𝐼
𝑜
𝑈
=
longitud de la intersecci
o
ˊ
n
longitud de la uni
o
ˊ
n
IoU= 
longitud de la uni 
o
ˊ
 n
longitud de la intersecci 
o
ˊ
 n
​
 
Por ejemplo, si un rango correcto es:

text
Copy
[100, 200]
Try:
|
y el resultado recuperado es:

text
Copy
[150, 250]
Try:
|
La intersección es:

text
Copy
[150, 200]
Try:
|
Su longitud es 50.

La unión es:

text
Copy
[100, 250]
Try:
|
Su longitud es 150.

Por tanto:

𝐼
𝑜
𝑈
=
50
150
=
0.3333
IoU= 
150
50
​
 =0.3333
7. Umbral utilizado
La clase define el siguiente umbral:

python
Copy
IOU_THRESHOLD = 0.05
Try:
|
Una fuente recuperada se considera encontrada cuando:

text
Copy
mismo file_path
y
IoU >= 0.05
Try:
|
Esta comprobación se realiza en _is_found():

python
Copy
def _is_found(
    self,
    retrieved_sources: list[MinimalSource],
    true_source: MinimalSource,
) -> bool:
Try:
|
El método revisa todas las fuentes recuperadas. Si encuentra una que pertenece al mismo archivo y supera el umbral de IoU, devuelve:

python
Copy
True
Try:
|
Si ninguna coincide, devuelve:

python
Copy
False
Try:
|
Por tanto, no es necesario recuperar exactamente el mismo rango de caracteres que aparece en el dataset. Basta con recuperar un fragmento del mismo archivo que se solape suficientemente con la fuente correcta.

8. Recall de una pregunta
Para cada pregunta se cuentan las fuentes correctas que han sido encontradas:

python
Copy
found_sources
Try:
|
Después se divide ese número entre el total de fuentes correctas:

python
Copy
self.question_recalls[question.question_id] = (
    found_sources / len(correct_sources)
)
Try:
|
La fórmula es:

Recall de la pregunta
=
fuentes correctas encontradas
fuentes correctas totales
Recall de la pregunta= 
fuentes correctas totales
fuentes correctas encontradas
​
 
Por ejemplo, si una pregunta tiene cuatro fuentes correctas y el buscador encuentra tres:

Recall
=
3
4
=
0.75
Recall= 
4
3
​
 =0.75
El recall de esa pregunta sería 0.75.

Si se encuentran todas las fuentes correctas:

Recall
=
4
4
=
1.0
Recall= 
4
4
​
 =1.0
Si no se encuentra ninguna:

Recall
=
0
4
=
0.0
Recall= 
4
0
​
 =0.0
9. Recall global o Recall@k
Una vez calculado el recall de todas las preguntas, el método calculate_recall_at_k() calcula la media:

python
Copy
def calculate_recall_at_k(self) -> None:
    if not self.question_recalls:
        raise ValueError("No questions have been evaluated.")

    total = sum(self.question_recalls.values())
    self.recall_at_k = total / len(self.question_recalls)
Try:
|
La fórmula es:

Recall@k
=
∑
recall de cada pregunta
n
u
ˊ
mero de preguntas evaluadas
Recall@k= 
n 
u
ˊ
 mero de preguntas evaluadas
∑recall de cada pregunta
​
 
Por ejemplo, si tres preguntas tienen estos recalls:

text
Copy
Pregunta 1: 1.00
Pregunta 2: 0.50
Pregunta 3: 0.75
Try:
|
El resultado global es:

Recall@k
=
1.00
+
0.50
+
0.75
3
=
0.75
Recall@k= 
3
1.00+0.50+0.75
​
 =0.75
Por tanto, el recall global sería 0.75, que equivale al 75 %.

Qué significa @k
La expresión Recall@k indica que la evaluación se realiza sobre los primeros k resultados recuperados para cada pregunta.

Por ejemplo:

bash
Copy
make run -- search_dataset \
  --dataset_path data/datasets/AnsweredQuestions/dataset_code_public.json \
  --k 5 \
  --save_directory data/output
Try:
|
En este caso, el archivo de resultados contiene como máximo cinco fuentes por pregunta.

Después, al ejecutar:

bash
Copy
make run -- evaluate \
  --student_search_results_path data/output/dataset_code_public.json \
  --dataset_path data/datasets/AnsweredQuestions/dataset_code_public.json
Try:
|
el resultado se muestra como:

text
Copy
Recall@k: 0.5758 (k=5, 99 preguntas)
Try:
|
Esto significa que:

Se utilizaron los cinco primeros resultados.
Se evaluaron 99 preguntas.
El recall medio fue 0.5758.
Expresado como porcentaje, equivale a 57.58 %.
Resultado de la prueba realizada
En la última ejecución se obtuvo:

text
Copy
-> Recall@k: 0.5758 (k=5, 99 preguntas)
Try:
|
Por tanto:

text
Copy
Recall@5 = 0.5758
Try:
|
o, expresado como porcentaje:

text
Copy
Recall@5 = 57.58 %
Try:
|
Esto significa que, de media, el buscador encontró el 57.58 % de las fuentes correctas dentro de los cinco resultados recuperados para cada pregunta.

Qué evalúa evaluate
El comando evaluate evalúa únicamente la recuperación de información:

text
Copy
¿El buscador ha recuperado las fuentes correctas?
Try:
|
No evalúa todavía la calidad de una respuesta generada por un modelo de lenguaje.

Por tanto, no mide:

Si la respuesta está bien redactada.
Si la respuesta responde correctamente a la pregunta.
Si la respuesta contiene información inventada.
Si la respuesta utiliza correctamente el contexto recuperado.
Esos aspectos pertenecerían a una evaluación posterior de la generación de respuestas.

Papel de evaluate en el proyecto
evaluate permite comparar distintas versiones del buscador de forma local.

El ciclo de trabajo es:

text
Copy
Modificar el buscador
        ↓
Ejecutar search_dataset
        ↓
Ejecutar evaluate
        ↓
Comparar el Recall@k
Try:
|
Por ejemplo, se pueden comparar diferentes valores de k:

text
Copy
Recall@1
Recall@5
Recall@10
Recall@20
Try:
|
También se pueden comparar:

Distintos tamaños de chunk.
Distintas estrategias de chunking.
Distintos tokenizadores.
Distintos métodos de puntuación.
Distintos índices de búsqueda.
El objetivo es comprobar si los cambios permiten recuperar más fuentes correctas.

Separación de responsabilidades
El diseño mantiene separadas la lógica y la interfaz:

Evaluate carga los datos y calcula la métrica.
StudentSearchResults y RagDataset validan la estructura mediante Pydantic.
CLI.evaluate valida las rutas y llama a Evaluate.
CLI.evaluate muestra el resultado por pantalla.
Las clases de lógica lanzan ValueError cuando encuentran un problema.
La CLI captura esos errores, los imprime por stderr y termina con código 1.
En resumen:

text
Copy
Evaluate calcula.
CLI muestra.
Pydantic valida.
Try:
|
Resumen final
evaluate compara las fuentes recuperadas por search_dataset con las fuentes correctas del dataset de referencia.

Para cada pregunta:

Busca sus resultados mediante question_id.
Comprueba cada fuente correcta.
Verifica que el archivo coincida.
Calcula el IoU de los rangos de caracteres.
Considera encontrada la fuente si el IoU es como mínimo 0.05.
Calcula el recall individual de la pregunta.
Después calcula la media de todos los recalls:

Recall@k
=
∑
recall de las preguntas
n
u
ˊ
mero de preguntas
Recall@k= 
n 
u
ˊ
 mero de preguntas
∑recall de las preguntas
​
 
La última prueba produjo:

text
Copy
Recall@5 = 0.5758
Try:
|
Es decir:

text
Copy
57.58 % de recall medio sobre 99 preguntas