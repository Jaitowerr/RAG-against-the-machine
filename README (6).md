*This project has been created as part of the 42 curriculum by aitorres.*

# RAG against the machine

Sistema RAG (*Retrieval-Augmented Generation*) que responde preguntas sobre el código fuente de **vLLM 0.10.1**: recupera los fragmentos exactos del repositorio que contienen la respuesta y se los entrega a un modelo local (**Qwen/Qwen3-0.6B**) para que redacte una respuesta basada solo en esa evidencia.

## Índice

1. [Descripción](#descripción)
2. [Instrucciones](#instrucciones)
3. [Arquitectura del sistema](#arquitectura-del-sistema)
4. [Estrategia de chunking](#estrategia-de-chunking)
5. [Método de recuperación](#método-de-recuperación)
6. [Ficheros que genera el sistema](#ficheros-que-genera-el-sistema)
7. [Modelos de datos](#modelos-de-datos)
8. [Referencia de comandos](#referencia-de-comandos)
9. [Análisis de rendimiento](#análisis-de-rendimiento)
10. [Decisiones de diseño](#decisiones-de-diseño)
11. [Dificultades encontradas](#dificultades-encontradas)
12. [Ejemplos de uso](#ejemplos-de-uso)
13. [Bonus](#bonus)
14. [Limitaciones conocidas](#limitaciones-conocidas)
15. [Recursos](#recursos)

---

## Descripción

Un modelo de lenguaje solo sabe lo que aprendió durante su entrenamiento. Reentrenarlo cada vez que cambia el mundo es lento y caro, así que en lugar de meter conocimiento *dentro* del modelo, se le da acceso a una fuente externa y se deja que consulte lo que necesita en el momento de responder.

Este proyecto construye ese ciclo completo sobre una base de código real (miles de archivos, cientos de miles de líneas):

1. **Indexar**: leer los `.py` y `.md` del repositorio, trocearlos y guardar un índice.
2. **Recuperar**: dada una pregunta, devolver las *k* fuentes más relevantes (archivo + rango de caracteres).
3. **Aumentar**: construir un contexto con el texto de esas fuentes.
4. **Generar**: pedir a Qwen3-0.6B una respuesta basada solo en ese contexto.
5. **Evaluar**: medir la calidad de la recuperación con *recall@k*.

El sistema **no entrena ni ajusta ningún modelo**. No usa claves de API: todo se ejecuta en local.

```text
Repositorio vLLM (.py y .md)
        ↓  index                     chunking + índice JSON en disco
Chunks (MinimalSource)
        ↓  search / search_dataset   BM25 → top-k fuentes
StudentSearchResults
        ↓  answer / answer_dataset   contexto + prompt + Qwen3-0.6B
StudentSearchResultsAndAnswer
        ↓  evaluate                  Recall@k contra el ground truth
```

La regla de oro del diseño: **todas las fases hablan el mismo idioma**. La unidad de información en todo el sistema es `MinimalSource` (`file_path`, `first_character_index`, `last_character_index`), exactamente el formato que espera el evaluador.

---

## Instrucciones

### Requisitos

- Python 3.10 o superior
- [`uv`](https://docs.astral.sh/uv/) como gestor de proyecto y paquetes
- Espacio en disco suficiente: el stack de deep learning y los pesos del modelo pueden ocupar varios GB
- GPU opcional: si hay CUDA disponible se usa; en caso contrario, CPU

### Instalación

```bash
make install        # equivale a: uv sync
```

Coloca el repositorio de vLLM en `data/raw/vllm-0.10.1/` y los datasets en `data/datasets/UnansweredQuestions/` y `data/datasets/AnsweredQuestions/`. Ni los datos, ni los pesos del modelo, ni las salidas generadas forman parte del repositorio (están en `.gitignore`).

### Reglas del Makefile

| Regla | Qué hace |
|---|---|
| `make install` | Instala las dependencias con `uv sync` |
| `make run -- <comando> [opciones]` | Ejecuta la CLI (`uv run python -m src <comando>`) |
| `make debug` | Ejecuta el programa principal con `pdb` |
| `make clean` | Elimina cachés temporales (`__pycache__`, `.mypy_cache`, …) |
| `make lint` | `flake8 .` + `mypy .` con los flags obligatorios del subject |
| `make lint-strict` | `flake8 .` + `mypy . --strict` |

### Ejecución rápida

Todos los comandos se lanzan como `uv run python -m src <comando> [opciones]` o, equivalentemente, `make run -- <comando> [opciones]`:

```bash
make run -- index
make run -- search "How is the KV cache managed?" --k 5
make run -- answer "What is the purpose of the scheduler?" --k 5
```

> **Nota sobre las flags.** Python Fire no impone un número fijo de guiones: `-k 3`, `--k 3` e incluso `---k 3` se interpretan igual. Es comportamiento de la librería y no afecta a la validación: el valor que llega a los métodos se valida igual sea cual sea la forma de escribir la flag.

### Entorno en 42 Madrid (poco espacio en disco)

Los ordenadores de la escuela tienen poco espacio en la raíz. El script `set-local.sh` redirige el entorno virtual y todas las cachés a `sgoinfre`:

```bash
export CALLME_STORAGE="/home/<login>/sgoinfre/callme"

export UV_CACHE_DIR="$CALLME_STORAGE/uv-cache"
export UV_PROJECT_ENVIRONMENT="$CALLME_STORAGE/venv"
export UV_PYTHON_INSTALL_DIR="$CALLME_STORAGE/python"

export HF_HOME="$CALLME_STORAGE/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub"

export TMPDIR="$CALLME_STORAGE/tmp"
export XDG_CACHE_HOME="$CALLME_STORAGE/xdg-cache"
```

```bash
uv cache dir          # ruta de caché por defecto
source set-local.sh
uv cache dir          # ahora apunta a sgoinfre; ya se puede usar make run
```

### Estructura del repositorio

```text
.
├── src/                    # módulo Python (uv run python -m src <comando>)
├── data/
│   ├── raw/                # corpus: vllm-0.10.1/
│   ├── processed/          # índices, manifiesto y caché (generado por index)
│   ├── datasets/
│   │   ├── UnansweredQuestions/
│   │   └── AnsweredQuestions/
│   └── output/
│       ├── search_results/<DatasetScope>/              # salida de search_dataset
│       └── search_results_and_answer/<DatasetScope>/   # salida de answer_dataset
├── pyproject.toml
├── uv.lock
├── Makefile
├── .gitignore
└── README.md
```

### Evaluación con la moulinette

El `evaluate` propio sirve para iterar rápido; el recall oficial lo calcula el ejecutable de la moulinette, que **el código nunca importa ni invoca**:

```bash
./moulinette evaluate_student_search_results \
  data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
  data/datasets/AnsweredQuestions/dataset_docs_public.json \
  --k 10 --max_context_length 2000
```

Con `list_valid_questions` se ve pregunta por pregunta cuáles tienen sus fuentes correctamente recuperadas, lo cual es muy útil para depurar los fallos de recall:

```bash
./moulinette list_valid_questions \
  data/output/search_results_and_answer/UnansweredQuestions/dataset_code_public.json \
  data/datasets/AnsweredQuestions/dataset_code_public.json \
  --k 10
```

---

## Arquitectura del sistema

El paquete `src/` se organiza en capas con responsabilidades separadas:

| Módulo | Responsabilidad |
|---|---|
| `__main__.py` | Punto de entrada: expone la clase `CLI` con `fire.Fire`, captura cualquier excepción no controlada y sale con código 1 |
| `cli.py` | Valida entradas, cronometra, imprime resultados; captura los `ValueError` de la lógica, los imprime por `stderr` y termina con código 1 |
| `index.py` | Clase `Index`: recorre el corpus, lee archivos, coordina el chunking y persiste el índice (uno por extensión) |
| `chunker.py` | Clase `Chunker`: decide cómo cortar cada archivo según su extensión |
| `search.py` | Clase `Search`: BM25 implementado a mano (tokenización, frecuencias, IDF, scoring) + caché en pickle |
| `search_dataset.py` | Clase `SearchDataset` (hereda de `Search`): lanza el motor sobre todas las preguntas de un dataset |
| `answer.py` | Clase `Answer` (hereda de `Search`): recupera, construye contexto y prompt, y llama a Qwen |
| `answer_dataset.py` | Clase `AnswerDataset` (hereda de `Answer`): genera respuestas por lotes a partir de un JSON de resultados |
| `evaluate.py` | Clase `Evaluate`: compara resultados con el ground truth mediante IoU y calcula Recall@k |
| `models.py` | Modelos Pydantic de todo el sistema |
| `api.py` | Bonus: API HTTP con FastAPI (`POST /search`, `POST /answer`) |
| `css.py` | `StyledBar`: subclase de `tqdm` con estilo unificado para todas las barras de progreso |
| `search_BM25.py` | Experimento comparativo: `SearchLibBM25`, misma interfaz pero con la librería `rank-bm25` (**no** es el buscador oficial) |

La jerarquía de herencia evita duplicar el motor de búsqueda: `SearchDataset`, `Answer` y `AnswerDataset` heredan todo el BM25 de `Search`. Si cambia el scoring o el tokenizador, `search_dataset` y `answer` mejoran gratis.

**Separación de responsabilidades:** `Search` busca, `Answer` construye el contexto y genera, Qwen redacta, y la CLI coordina y muestra.

### Ciclo de vida de una respuesta (`answer`)

```text
query, k
   │
   ▼
Answer(query, k)                       # solo crea el objeto; aún no busca
   │
   ▼
build_context()
   ├── retrieve_sources()
   │      ├── prepare()                # cargar índice, tokenizar, contar términos, media
   │      └── search()                 # BM25 → hasta k MinimalSource
   ├── _chunk_text(source)             # localiza el chunk por sus 3 claves y extrae su texto
   └── "\n\n".join(chunks)             → context
   │
   ▼
build_prompt(context)                  → instrucciones + contexto + pregunta + "Answer:"
   │
   ▼
generate_answers([prompt])             # aquí se llama a Qwen por primera vez
```

Hasta `build_prompt` la IA no participa: todo es recuperación y preparación de información local.

---

## Estrategia de chunking

El tamaño máximo por defecto es **2000 caracteres** (`--max_chunk_size`), el límite del enunciado: la moulinette rechaza cualquier fuente más larga y una sola invalida toda la salida. Se valida antes de hacer nada: debe ser un entero positivo y no superar 2000 (mensaje claro y código de salida 1, sin traceback).

La clase `Chunker` mantiene un diccionario de estrategias `{extensión: método}` (`.py → _split_python`, `.md → _split_markdown`) con un método genérico de reserva que corta cada `max_chunk_size` caracteres. Añadir un formato nuevo es añadir una entrada, y una extensión desconocida nunca rompe el sistema.

### Python (`_split_python`)

Corta en **líneas en blanco**, que en código real suelen coincidir con los límites entre funciones y clases, de modo que cada chunk tiende a contener funciones completas. No se usa el módulo `ast`.

El separador no es solo `\n\n`, sino la expresión regular `\n(?:[ \t]*\n)+`: dos o más saltos de línea con espacios o tabuladores entre medias, porque el repositorio real contiene `\n\n\n` y variantes. Se elige el **último separador que quepa en la ventana**. Si no hay ninguno, se retrocede al último salto de línea simple; y si tampoco lo hay, se corta justo en `max_chunk_size`.

### Markdown (`_split_markdown`)

Corta en los mismos separadores de línea en blanco, que en prosa corresponden a **párrafos**, así que un párrafo nunca se parte por la mitad. No se corta específicamente por encabezados `#`.

### Solapamiento

Cada chunk repite hasta un **20 %** del anterior (máximo **60 caracteres**) cuando su tamaño es suficiente (`_overlap_size` devuelve 0 para chunks de menos de 120 caracteres). Así, una respuesta situada justo en la frontera de un corte existe completa en los dos chunks vecinos y BM25 puede encontrarla desde cualquiera de ellos.

### Representación

Los chunks se manejan como *spans* `(start, end)`, no como copias. En `save_index` se recorta el texto con `content[start:end]` y se guarda en la entrada del índice; el archivo original nunca se modifica y sigue siendo la fuente de verdad.

---

## Método de recuperación

El enunciado exige TF-IDF o BM25. Se eligió **BM25** y se implementó **a mano** en `search.py` (`Counter` + `math.log`), sin librería. `rank-bm25` queda solo como experimento comparativo en `search_BM25.py`.

### Por qué BM25 y no TF-IDF

TF-IDF multiplica el `tf` a secas: una palabra repetida 30 veces puntúa 30 veces más y los documentos largos ganan solo por ser largos. BM25 corrige ambas cosas:

- **Saturación de `tf`**: repetir una palabra rinde cada vez menos. En código, donde un identificador puede aparecer decenas de veces en un chunk, evita que la repetición machaque al contenido.
- **Normalización por longitud** (parámetro `b`): penaliza o premia según el chunk se aleje de la longitud media. Los chunks van de unas pocas líneas a 2000 caracteres; sin normalización, los largos ganarían sin ser más relevantes.

### Fórmula (Okapi BM25 con IDF siempre positivo)

$$\mathrm{IDF}(t) = \ln\left(\frac{N - df + 0.5}{df + 0.5} + 1\right)$$

$$\mathrm{score}(q, d) = \sum_{t \in q} \mathrm{IDF}(t) \cdot \frac{tf \cdot (k_1 + 1)}{tf + k_1 \cdot \left(1 - b + b \cdot \frac{|d|}{avgdl}\right)}$$

donde `N` es el número de chunks, `df` en cuántos chunks aparece el término, `tf` cuántas veces aparece en el chunk, `|d|` la longitud del chunk en tokens y `avgdl` la longitud media.

**Parámetros activos: `k1 = 1.2`, `b = 0.45`.** Son valores ajustados empíricamente a partir de los estándar de la literatura (`k1 = 1.2`, `b = 0.75`) para mejorar el recall sobre este corpus. El `+1` dentro del logaritmo garantiza IDF positivo: va de ≈0.48 para una palabra presente en casi todos los chunks (`the`) a ≈10.12 para una que no aparece nunca.

### Por qué a mano

- **Control total del pipeline**: caché, tokenizador con separación de camelCase y orden determinista se integran sin pelear con las estructuras internas de una librería.
- **Transparencia**: cada término de la fórmula es una línea legible (`_idf`, `_score_chunk`).
- **Comparación**: `search_BM25.py` reimplementa la misma interfaz con `BM25Okapi` y permite contrastar resultados con la implementación propia.

### Detalles del motor

- **Tokenizador**: parte camelCase (`SamplingParams → sampling params`), pasa a minúsculas y aplica `re.findall(r"[a-z0-9]+", ...)`. Usar la misma función en pregunta y chunks es lo que hace que `OpenAI?` encuentre `openai` y que `samplingparams` encuentre `SamplingParams`.
- **Estructuras**: `entries` (chunks tal cual los escribió `index`, con su `text`), `tokens` (lista de listas, posición paralela a `entries`), `term_freqs` (un `Counter` por chunk), `doc_freq` (término → en cuántos chunks aparece; **no** es frecuencia total: una palabra puede aparecer 4.703 veces pero, si todas están en 3 chunks, su `doc_freq` es 3), `query_tokens` y `average_chunk_length`.
- **Determinismo**: `search()` solo considera chunks con score > 0 y ordena con el sort estable de Python; los empates conservan el orden del índice. Misma entrada, misma salida.
- **Preparar una sola vez**: `prepare()` enciende todo (cargar, tokenizar query, tokenizar corpus, contar términos, media) y `search()` acepta una `query` opcional que reutiliza el estado. Es lo que permite a `search_dataset` pagar la preparación una vez y lanzar 200 preguntas encima.
- **Selección de índice**: `SearchDataset` deduce el índice por el nombre del dataset (`dataset_code_*.json → index_py.json`, `dataset_docs_*.json → index_md.json`), de modo que las preguntas de documentación se resuelven contra la documentación y las de código contra el código, con menos ruido. Si con ese índice una pregunta no da resultados, hay un *fallback* que busca en todos los índices a la vez.

---

## Ficheros que genera el sistema

Tres ficheros distintos para tres trabajos distintos:

| Fichero | Formato | Qué guarda | Por qué ese formato |
|---|---|---|---|
| `index_py.json` / `index_md.json` | JSON | Chunks con `file_path`, `first_character_index`, `last_character_index`, `text` | Formato de intercambio con el evaluador, legible y depurable |
| `cache/search_cache_*.pkl` | Pickle | Estado preparado del motor: tokens, frecuencias, longitud media | Estado interno de Python, binario y rápido |
| `manifest_index.json` | JSON | `max_chunk_size` + ruta → huella SHA-256 del contenido | Detección de cambios para la indexación incremental |

Todos viven en `data/processed/`.

### 1. El índice (`index_py.json`, `index_md.json`)

Es el producto de `index`. Cada entrada:

```json
{
  "file_path": "data/raw/vllm-0.10.1/vllm/sampling_params.py",
  "first_character_index": 3571,
  "last_character_index": 5547,
  "text": "    n: int = 1\n    ..."
}
```

¿Por qué JSON y no pickle o una base de datos? Primero, es el formato que espera el mundo exterior (los resultados para el evaluador son JSON con esas mismas claves). Segundo, es legible por una persona. Tercero, guarda **rangos** de caracteres además del texto: la fuente de verdad es siempre el archivo original, así que se puede reindexar con otro `max_chunk_size` sin arrastrar estado. Se separa por extensión para poder elegir en qué mitad del corpus se busca.

### 2. La caché de búsqueda (`search_cache_py.pkl`, `search_cache_md.pkl`, `search_cache_all.pkl`)

El trabajo caro de la búsqueda no es puntuar, es **preparar**: cargar el JSON, tokenizar ~13.000 chunks, contar `term_freqs` y `doc_freq`, y calcular la media (~0,6 s). La caché guarda ese estado ya preparado, un pickle por índice.

Se usa pickle y no JSON porque es estado interno de Python (`Counter` y listas de listas que nadie más lee): se serializa sin pérdida de tipo y carga más rápido. Lleva dentro una **huella de validez**: una lista de tuplas `(ruta, tamaño, mtime_ns)` de cada `index_*.json`. Antes de usarla se comprueba que coincida con los ficheros actuales; si se reindexó, la caché queda obsoleta y se recalcula sola. Nunca se devuelve una caché desactualizada.

### 3. El manifiesto (`manifest_index.json`)

Soporte de la indexación incremental. Guarda el `max_chunk_size` de la última indexación y un diccionario **ruta → SHA-256** del contenido de cada archivo (`hashlib.sha256(file_path.read_bytes()).hexdigest()`).

Un matiz: esto es un **hash, no cifrado**. No hay clave ni nada descifrable; SHA-256 es una función de resumen de una sola dirección que actúa como "número de serie" del contenido. En cada ejecución de `index` se recalcula y se compara con el manifiesto para clasificar los archivos:

| Estado | Significado | Acción |
|---|---|---|
| `unchanged` | Misma huella | Se reutilizan sus chunks del índice anterior |
| `modified` | Huella distinta | Se vuelve a trocear |
| `new` | No estaba en el manifiesto | Se trocea |
| `deleted` | Estaba y ya no existe | Sus chunks desaparecen del índice |

Si además cambió `max_chunk_size`, se fuerza un reindexado completo. Reindexar un repositorio sin cambios cuesta casi nada, y tocar un archivo solo cuesta trocear ese archivo.

---

## Modelos de datos

Todo JSON que entra o sale del sistema pasa por un modelo Pydantic definido en `models.py`:

| Modelo | Uso |
|---|---|
| `MinimalSource` | Una fuente: `file_path`, `first_character_index`, `last_character_index` |
| `UnansweredQuestion` | Pregunta con `question_id` (UUID por defecto) y `question` |
| `AnsweredQuestion` | Pregunta + `sources` + `answer` |
| `RagDataset` | Dataset: `rag_questions` |
| `MinimalSearchResults` | Resultado por pregunta: `question_id`, `question`, `retrieved_sources` |
| `MinimalAnswer` | Lo anterior + `answer` |
| `StudentSearchResults` | Salida de `search_dataset`: `search_results` + `k` |
| `StudentSearchResultsAndAnswer` | Salida de `answer_dataset`: `search_results` (con respuesta) + `k` |

El campo `file_path` se escribe **exactamente igual que en el corpus** (`data/raw/vllm-0.10.1/...`), porque el evaluador lo compara literalmente.

---

## Referencia de comandos

| Comando | Qué hace | Parámetros |
|---|---|---|
| `index` | Lee `data/raw/`, trocea y construye el índice en `data/processed/` | `--max_chunk_size` (por defecto 2000, máx. 2000) |
| `search` | Top-k fuentes para una pregunta; solo imprime | `query`, `--k` |
| `search_dataset` | Búsqueda sobre un dataset completo → `StudentSearchResults` | `--dataset_path`, `--k`, `--save_directory` |
| `answer` | Busca y genera una respuesta para una pregunta | `query`, `--k` |
| `answer_dataset` | Genera respuestas a partir de un JSON de `search_dataset` → `StudentSearchResultsAndAnswer` | `--student_search_results_path`, `--save_directory` |
| `evaluate` | Calcula Recall@k contra un dataset de referencia | `--student_search_results_path`, `--dataset_path` |
| `serve` | (Bonus) Arranca la API HTTP | — |

Flujo típico: `index → search_dataset → answer_dataset → evaluate`. Las variantes de una sola pregunta (`search`, `answer`) sirven para pruebas manuales.

### `index`

Recorre `data/raw/vllm-0.10.1/` con `rglob`, se queda con `.py` y `.md`, lee los archivos (con barra de progreso), trocea con el `Chunker` y persiste un JSON por extensión. Todo pasa por `update_index`: si no hay cambios responde *Índice al día* sin reindexar; si los hay, reutiliza los chunks de los archivos intactos y solo re-trocea los nuevos y modificados. Imprime estadísticas (nuevos / modificados / borrados / sin cambios / chunks totales) y el tiempo por fase y total en `HH:MM:SS.microsegundos`.

### `search`

Valida la query (no vacía) y `k` (entero estrictamente positivo), prepara el índice (o carga la caché), puntúa todos los chunks, ordena y devuelve el top-k:

```text
Resultados para 'How to configure the OpenAI server?':
    1. data/raw/vllm-0.10.1/vllm/entrypoints/openai/server.py [16953:18260]
    2. ...
Tiempo total: 00:00:00.612345
```

### `search_dataset`

Valida el fichero de entrada (existe, `.json`, legible), `k` y la carpeta de salida. Guard crítico: **la carpeta de salida no puede ser la del dataset de entrada**, porque el fichero de salida se llama igual y lo pisaría. La comparación usa `.resolve()` para que `data/output` y `./data/output` cuenten como la misma carpeta, y corre antes del `mkdir`, así que en el caso prohibido no se crea ni escribe nada.

Después carga el dataset (exige `rag_questions` como lista no vacía y `question_id` + texto en cada pregunta, con errores que indican la posición), prepara el índice **una sola vez** y busca cada pregunta. Guarda `StudentSearchResults` con el mismo nombre que el fichero de entrada:

```json
{
  "search_results": [
    {
      "question_id": "189c8b8a-...",
      "question": "What activation formats does ...?",
      "retrieved_sources": [
        {"file_path": "data/raw/vllm-0.10.1/docs/design/fused_moe_modular_kernel.md",
         "first_character_index": 16953, "last_character_index": 18260}
      ]
    }
  ],
  "k": 10
}
```

El campo `k` va dentro del JSON para que el fichero cuente por sí mismo cómo se generó.

### `answer`

Construye el contexto con las fuentes recuperadas y el prompt:

```text
Answer the question using only the provided context.

Context:
<texto de los chunks recuperados>

Question:
What is the purpose of the scheduler?

Answer:
```

Si no hay contexto, informa y **no llama al modelo**. Si lo hay, carga Qwen una sola vez (`pipeline("text-generation", model="Qwen/Qwen3-0.6B")`, `cuda` si hay GPU y `cpu` en caso contrario) y genera con `max_new_tokens=200`, `do_sample=False` (*greedy*, determinista), `return_full_text=False` y `stop_strings=["\nQuestion", "\nAnswer"]`. La CLI imprime el `AnsweredQuestion` resultante en JSON.

### `answer_dataset`

No vuelve a buscar: lee el JSON de `search_dataset` (validado con `model_validate_json` contra `StudentSearchResults`), reutiliza las fuentes ya recuperadas, reconstruye los contextos y genera las respuestas **por lotes** (prompts agrupados de 2 en 2 con `padding_side="left"`). Las preguntas con contexto vacío reciben `answer: ""` sin gastar modelo. Salida: `StudentSearchResultsAndAnswer` con el mismo nombre de fichero en `--save_directory`.

### `evaluate`

Carga y valida ambos ficheros con Pydantic, comprueba que toda pregunta del dataset con fuentes tenga resultado en el fichero del estudiante (`validate_question_ids`) y, para cada fuente correcta, comprueba `_is_found`: **mismo `file_path` exacto** e **IoU ≥ 0.05** entre los rangos de caracteres.

$$\mathrm{IoU} = \frac{\text{longitud de la intersección}}{\text{longitud de la unión}}$$

Por ejemplo, con un rango correcto `[100, 200]` y uno recuperado `[150, 250]`: intersección 50, unión 150, IoU ≈ 0.33 (cuenta como encontrada).

El recall de cada pregunta es `fuentes_encontradas / fuentes_correctas`, y la métrica global es la media:

$$\mathrm{Recall@k} = \frac{\sum \text{recall de cada pregunta}}{\text{número de preguntas}}$$

Ejemplo del formato de salida:

```text
-> Recall@k: 0.5758 (k=5, 99 preguntas)
```

`evaluate` mide **solo la recuperación**, no la calidad de la redacción; esa se comprueba aparte con las tres preguntas válidas del script de corrección.

---

## Análisis de rendimiento

Límites del enunciado frente a resultados medidos con la moulinette (última medición: 24/09/2026, `k = 5`):

| Métrica | Límite | Resultado | Estado |
|---|---|---|---|
| Recall@5 documentación | ≥ 0.80 | `docs_public` 0.8600 · `docs_private` 0.8300 | ✔ |
| Recall@5 código | ≥ 0.50 | `code_public` 0.6465 · `code_private` 0.5200 | ✔ |
| Indexado completo | ≤ 5 min | Muy por debajo; reindexar sin cambios es casi instantáneo | ✔ |
| 200 preguntas (`search_dataset`) | ≤ 90 s | ~33 preguntas/s (99 preguntas en ~3,5 s) | ✔ |

El punto más ajustado es `code_private` (0.52 frente a un mínimo de 0.50).

**La lección de rendimiento más importante:** la primera versión calculaba `_average_chunk_length()` dentro de `_score_chunk`, que se ejecuta ~13.000 veces por búsqueda, y cada llamada volvía a sumar las longitudes de los ~13.000 chunks: coste cuadrático, unos **5,5 s por consulta**. Como la media no cambia durante la búsqueda, se calcula una vez en `prepare()` y se guarda en `self.average_chunk_length`: **~0,6 s por búsqueda con resultados idénticos**. La caché pickle elimina incluso esa preparación en ejecuciones repetidas.

> Los cambios en el buscador se validan con el ciclo *modificar → `search_dataset` → `evaluate` → comparar Recall@k*, que permite comparar tamaños de chunk, estrategias de chunking, tokenizadores y parámetros de BM25.

---

## Decisiones de diseño

- **Lógica separada de la interfaz.** Las clases de lógica (`Index`, `Search`, `Evaluate`, …) señalan problemas lanzando `ValueError` con mensajes claros; la CLI los captura, los imprime por `stderr` y termina con código 1. **Nunca hay tracebacks**, incluso con: query vacía o de puro ruido, `k` = 0, negativo, booleano, decimal o no numérico, índice inexistente / malformado / vacío, dataset inexistente, ilegible o sin preguntas, y carpeta de salida inválida.
- **Un solo formato de datos de punta a punta.** `MinimalSource` lo produce `index`, lo devuelve `search`, lo consume `answer` y lo evalúa `evaluate`. Sin conversiones entre fases.
- **Pydantic en las fronteras.** Todo JSON que entra o sale pasa por un modelo.
- **Herencia en lugar de copia.** El motor BM25 existe en un único lugar.
- **Determinismo.** Sort estable, `do_sample=False` y mismos pesos del modelo: misma entrada, misma salida.
- **Índices separados por extensión** para reducir el ruido entre código y documentación.
- **Rutas siempre configurables** (`--dataset_path`, `--save_directory`, `--student_search_results_path`); la única ubicación por defecto es la del corpus y el índice, tal como fija el subject.
- **Herramientas usadas:** Python 3.10+, `uv`, Python Fire (CLI), `tqdm` (barras, envueltas en `StyledBar`), Pydantic, `flake8` y `mypy` (`make lint` / `make lint-strict`), `transformers` con Qwen/Qwen3-0.6B en local.

### Modelo

El modelo por defecto y único soportado es **Qwen/Qwen3-0.6B**, cargado en local con `transformers` (pipeline `text-generation`; GPU si está disponible, CPU en caso contrario). No se usan claves de API. Por ahora no se soportan otros modelos.

---

## Dificultades encontradas

| Dificultad | Solución |
|---|---|
| **Bucle cuadrático oculto**: la longitud media se recalculaba 13.000 veces por consulta (5,5 s/query) | Se calcula una vez en `prepare()` (0,6 s) |
| **Separadores irregulares del corpus**: `\n\n\n` o `\n \n` hacían que el corte cayera en medio del separador y dejaba chunks que empezaban con líneas en blanco | Regex `\n(?:[ \t]*\n)+` y elegir el último separador que quepa en la ventana |
| **Rutas distintas que son la misma**: comparar `save_directory` con la carpeta del dataset como *strings* fallaba con `./data/output` | `.resolve()` sobre ambas rutas, y el guard corre antes del `mkdir` |
| **Semántica traicionera de tipos en Python**: `isinstance(True, int)` es `True` e `int(2.5)` trunca en silencio | Los `bool` se rechazan antes de convertir; los `float` con decimales, antes del `int()` |
| **Presupuesto de 90 s para 200 preguntas** | Preparar una vez y buscar N veces, reforzado con la caché pickle |
| **Poco espacio en disco en 42** | `set-local.sh` redirige entorno virtual y cachés a `sgoinfre` |

---

## Ejemplos de uso

Secuencia completa, tal y como la ejecutan los scripts de corrección:

```bash
make install                                         # uv sync
make run -- index                                    # 1. construir/actualizar el índice

# Prueba rápida de una pregunta
make run -- search "How is the KV cache managed?" --k 5

# 2. Búsqueda masiva sobre los 4 datasets
for d in docs_public docs_private code_public code_private; do
  make run -- search_dataset \
    --dataset_path data/datasets/UnansweredQuestions/dataset_$d.json \
    --k 5 \
    --save_directory data/output/search_results/UnansweredQuestions
done

# 3. Medir la calidad contra el ground truth (evaluate propio)
make run -- evaluate \
  --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
  --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json

# 4. Generar respuestas en bloque
make run -- answer_dataset \
  --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
  --save_directory data/output/search_results_and_answer/UnansweredQuestions

# 5. Uso interactivo y bonus
make run -- answer "What is the purpose of the scheduler?" --k 5
make run -- serve                                    # API HTTP
make lint && make lint-strict
```

Salida de `answer`:

```json
{
  "question": "What is the purpose of the scheduler?",
  "sources": [
    {"file_path": "data/raw/vllm-0.10.1/vllm/core/scheduler.py",
     "first_character_index": 1000, "last_character_index": 1800}
  ],
  "answer": "The scheduler manages the KV cache and schedules requests..."
}
```

---

## Bonus

| Bonus | Estado | Detalle |
|---|---|---|
| Indexación incremental | ✔ Implementado | Huellas SHA-256 + `manifest_index.json`; solo se re-trocean archivos nuevos o modificados |
| Caché | ✔ Implementado | Pickle del estado del buscador, invalidado por huella `(ruta, tamaño, mtime_ns)` |
| API HTTP local | ✔ Implementado | FastAPI: `POST /search`, `POST /answer` |
| Embeddings semánticos | ✘ No implementado | — |
| Recuperación híbrida | ✘ No implementado | — |

### API HTTP

```bash
uv run python -m src serve
# o bien: uv run uvicorn src.api:app --host 127.0.0.1 --port 8000
```

`src.api:app` indica el paquete `src`, el archivo `api.py` y la variable `app`; `--host 127.0.0.1` limita el acceso a la propia máquina.

- `POST /search` con `{"query": "...", "k": 5}` → lista de `MinimalSource`
- `POST /answer` con el mismo cuerpo → un `AnsweredQuestion` completo
- Query vacía o `k ≤ 0` → HTTP 400 con mensaje claro; pregunta sin fuentes → 404
- Documentación interactiva autogenerada en `/docs`

---

## Limitaciones conocidas

- La recuperación es **puramente léxica**: una pregunta muy parafraseada, sin palabras en común con el chunk, puede no recuperar la fuente correcta. Es el motivo probable de que `code_private` esté cerca del umbral.
- Qwen3-0.6B tiene límites conocidos de razonamiento; las respuestas pueden ser parciales aunque las fuentes recuperadas sean las correctas.
- El solapamiento entre chunks aumenta ligeramente su tamaño efectivo; el tamaño total de cada fuente se mantiene dentro del límite de 2000 caracteres.

Como mejoras futuras naturales: embeddings semánticos con un modelo ligero de CPU (p. ej. `all-MiniLM-L6-v2`) y recuperación híbrida combinando ambos rankings.

---

## Recursos

**Documentación y referencias**

- Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (2020): https://arxiv.org/abs/2005.11401
- Robertson & Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond* (2009): https://doi.org/10.1561/1500000019
- Manning, Raghavan & Schütze, *Introduction to Information Retrieval*: https://nlp.stanford.edu/IR-book/
- vLLM: https://docs.vllm.ai
- Qwen/Qwen3-0.6B: https://huggingface.co/Qwen/Qwen3-0.6B
- Hugging Face Transformers, pipelines: https://huggingface.co/docs/transformers/main_classes/pipelines
- Pydantic: https://docs.pydantic.dev
- Python Fire: https://github.com/google/python-fire
- uv: https://docs.astral.sh/uv/
- FastAPI: https://fastapi.tiangolo.com

El corpus es el repositorio público de vLLM 0.10.1; los datasets públicos y privados y la moulinette son material proporcionado por 42.

**Uso de la IA**

La IA se utilizó como herramienta de aprendizaje y apoyo, no como sustituto de la comprensión:

- **Explicación de conceptos**: flujo de `transformers` y del `pipeline`, funcionamiento de RAG y de BM25.
- **Depuración**: detección del bucle cuadrático en el cálculo de la longitud media y revisión de la validación de entradas.
- **Revisión**: comparación del código con el subject para detectar inconsistencias entre README e implementación.
- **Documentación**: redacción y estructuración de este README.

Las decisiones de diseño, la implementación y las mediciones de rendimiento son propias, y todo el código generado o sugerido con ayuda de la IA ha sido revisado, probado y entendido antes de incorporarse.
