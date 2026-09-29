_Este proyecto ha sido creado como parte del currículo de 42 por aitorres._

<div align="center">

# RAG against the machine

**Generación Aumentada por Recuperación**

_42 Madrid - Fundación Telefónica_

![Python 3.10](https://img.shields.io/badge/Python-3.10-blue.svg) ![uv](https://img.shields.io/badge/Package_Manager-uv-orange.svg) ![Qwen3-0.6B](https://img.shields.io/badge/LLM-Qwen--3--0.6B-green.svg) ![Mypy Strict](https://img.shields.io/badge/Lint-Strict-red.svg)

</div>

---

Sistema local de generación aumentada mediante recuperación (RAG) que responde preguntas sobre el código fuente de **vLLM 0.10.1**. El sistema recupera los fragmentos relevantes mediante un motor de búsqueda BM25 implementado manualmente y se los proporciona a **Qwen/Qwen3-0.6B**, que genera una respuesta basada únicamente en la evidencia recuperada.

## Contenido

1. [Descripción](#descripci%C3%B3n)

2. [Instrucciones](#instrucciones)

3. [Arquitectura](#arquitectura-del-sistema)

4. [Estrategia de chunking](#estrategia-de-chunking)

5. [Método de recuperación](#m%C3%A9todo-de-recuperaci%C3%B3n)

6. [Archivos generados](#archivos-generados)

7. [Modelos de datos](#modelos-de-datos)

8. [Referencia de comandos](#referencia-de-comandos)

9. [Análisis del rendimiento](#an%C3%A1lisis-del-rendimiento)

10. [Decisiones de diseño](#decisiones-de-dise%C3%B1o)

11. [Dificultades](#dificultades)

12. [Ejemplo de uso](#ejemplo-de-uso)

13. [Bonus](#bonus)

14. [Limitaciones conocidas](#limitaciones-conocidas)

15. [Recursos y uso de IA](#recursos-y-uso-de-ia)

<br>

## Descripción

El proyecto implementa el flujo RAG completo sobre una base de código real:

1. **Indexación:** lee los archivos `.py` y `.md`, los divide en fragmentos y guarda los índices.

2. **Recuperación:** recibe una pregunta y devuelve los rangos de código fuente más relevantes.

3. **Aumento:** extrae el texto de los fragmentos recuperados y construye un contexto.

4. **Generación:** envía el contexto y la pregunta a Qwen/Qwen3-0.6B.

5. **Evaluación:** compara las fuentes recuperadas con la referencia mediante Recall@k.

El sistema no entrena ni ajusta ningún modelo. Se ejecuta localmente y no necesita claves de API.

```text
Repositorio vLLM (.py y .md)
        |
        | make run -- index
        v
Fragmentos e índices JSON
        |
        | make run -- search_dataset
        v
Recuperación BM25 de los top-k
        |
        | make run -- answer / answer_dataset
        v
Contexto + prompt + Qwen/Qwen3-0.6B
        |
        | make run -- evaluate
        v
Evaluación Recall@k
```

La unidad común de información es `MinimalSource`, que contiene `file_path`, `first_character_index` y `last_character_index`. Este formato se utiliza en todo el flujo de recuperación y evaluación.

<br>

## Instrucciones

### Requisitos

* Python 3.10 o superior.

* `uv` para gestionar el entorno y las dependencias.

* Se pueden necesitar varios gigabytes para las dependencias de aprendizaje automático y los pesos del modelo.

* La GPU es opcional. Se utiliza CUDA cuando está disponible; en caso contrario, el sistema funciona en CPU.

### Instalación y ejecución

El proyecto está diseñado para ejecutarse mediante el `Makefile`. La regla `make run` sincroniza primero el entorno con `uv sync`, ejecuta el comando solicitado y limpia después las cachés temporales de Python.

```bash
make install
make run -- index
make run -- search '"How is the KV cache managed?" --k 5'
make run -- answer '"What is the purpose of the scheduler?" --k 5'
```

`make install` sincroniza el entorno y las dependencias. En el uso normal, `make run -- <comando>` es suficiente porque vuelve a sincronizar el entorno antes de ejecutar el comando.

El repositorio de vLLM debe colocarse en:

```text
data/raw/vllm-0.10.1/
```

Los datasets deben colocarse en:

```text
data/datasets/UnansweredQuestions/
data/datasets/AnsweredQuestions/
```

El corpus, los datasets, los pesos del modelo, los índices generados, las cachés y los ficheros de salida no deben incluirse en el repositorio.

### Reglas del Makefile

| Regla | Descripción |
| --- | --- |
| `make install` | Sincroniza las dependencias mediante `uv sync`. |
| `make run -- <comando> [opciones]` | Sincroniza el entorno y ejecuta `uv run python -m src <comando>`. |
| `make debug` | Inicia el módulo principal mediante `pdb`. |
| `make clean` | Elimina cachés temporales de Python y de comprobación de tipos. |
| `make lint` | Ejecuta `flake8` y la configuración no estricta de `mypy`. |
| `make lint-strict` | Ejecuta `flake8` y `mypy --strict`. |

### Estructura del repositorio

```text
.
├── src/
│   ├── __main__.py
│   ├── cli.py
│   ├── index.py
│   ├── chunker.py
│   ├── search.py
│   ├── search_dataset.py
│   ├── answer.py
│   ├── answer_dataset.py
│   ├── evaluate.py
│   ├── models.py
│   ├── api.py
│   └── css.py
├── data/
│   ├── raw/vllm-0.10.1/
│   ├── processed/
│   ├── datasets/
│   └── output/
├── pyproject.toml
├── uv.lock
├── Makefile
├── .gitignore
└── README.md
```

<br>

## Arquitectura del sistema

El sistema está dividido en capas con responsabilidades separadas:

| Módulo | Responsabilidad |
| --- | --- |
| `__main__.py` | Punto de entrada que expone la clase `CLI` mediante Python Fire. |
| `cli.py` | Valida argumentos, coordina operaciones, mide tiempos y muestra errores. |
| `index.py` | Recorre el corpus, coordina el chunking y escribe un índice JSON por extensión. |
| `chunker.py` | Divide los archivos según su extensión y el tamaño máximo configurado. |
| `search.py` | Implementa la tokenización, la puntuación BM25, la preparación del índice y la caché. |
| `search_dataset.py` | Ejecuta la recuperación para todas las preguntas de un dataset. |
| `answer.py` | Recupera fuentes, construye el contexto y el prompt, y llama a Qwen. |
| `answer_dataset.py` | Genera respuestas para un fichero completo de resultados de búsqueda por lotes. |
| `evaluate.py` | Compara rangos recuperados con las fuentes de referencia y calcula Recall@k. |
| `models.py` | Define los modelos Pydantic usados en los límites JSON. |
| `api.py` | Proporciona la interfaz local opcional con FastAPI. |
| `css.py` | Proporciona una barra de progreso `tqdm` común y estilizada. |

Para una petición individual de `answer`, el flujo es:

```text
Pregunta y k
      |
      v
Recuperar objetos MinimalSource con BM25
      |
      v
Leer los rangos correspondientes de los archivos originales
      |
      v
Construir el contexto y el prompt
      |
      v
Generar con Qwen/Qwen3-0.6B
      |
      v
Devolver un AnsweredQuestion
```

El modelo no interviene durante la indexación ni durante la recuperación. Solo se llama después de construir el contexto.

<br>

## Estrategia de chunking

El tamaño máximo por defecto es de **2.000 caracteres**, que también es el máximo aceptado por el enunciado. Se puede configurar con `--max_chunk_size`, pero se rechazan valores superiores a 2.000.

`Chunker` mantiene una estrategia por extensión:

* Los archivos `.py` utilizan la estrategia de Python.

* Los archivos `.md` utilizan la estrategia de Markdown.

* Las extensiones desconocidas utilizan un fallback genérico basado en caracteres.

### Archivos Python y Markdown

Los formatos soportados se dividen primero en separadores de líneas en blanco. El separador reconoce varias líneas en blanco y líneas que contienen espacios o tabuladores:

```text
\\n(?:[ \\t]*\\n)+
```

El separadorizador elige el último separador adecuado dentro de la ventana permitida. Si no existe un separador de líneas en blanco apropiado, utiliza el último salto de línea simple y, como último recurso, corta en el límite máximo de caracteres.

Este enfoque intenta conservar los límites naturales entre funciones, clases, párrafos y secciones. Sin embargo, una función o un párrafo que supere el límite puede dividirse para garantizar que ningún fragmento supere los 2.000 caracteres.

### Solapamiento

Cada fragmento suficientemente grande repite hasta el 20 % del fragmento anterior, con un máximo absoluto de 60 caracteres. Los fragmentos de menos de 120 caracteres no reciben solapamiento. Esto reduce el riesgo de perder información en una frontera.

Los fragmentos se representan inicialmente como intervalos `(start, end)`. El archivo original sigue siendo la fuente de verdad; el texto se copia al índice JSON cuando este se guarda.

## Método de recuperación

El enunciado exige TF-IDF o BM25. Este proyecto utiliza **BM25**, implementado directamente en `search.py` sin utilizar la librería `rank-bm25` en el flujo oficial. `search_BM25.py` es un experimento opcional de comparación que utiliza la librería externa.

### ¿Por qué BM25 en lugar de TF-IDF?

BM25 se eligió porque resuelve dos problemas habituales en la recuperación de código:

* **Saturación de la frecuencia del término:** repetir muchas veces un identificador no debe aumentar indefinidamente su relevancia de forma lineal.

* **Normalización por longitud:** los fragmentos largos no deben posicionarse arriba únicamente porque contienen más tokens.

La implementación utiliza las siguientes fórmulas:

$\
$

$\
$

Los parámetros utilizados son:

```text
k1 = 1.2
b  = 0.45
```

El mismo tokenizador se aplica a las preguntas y a los fragmentos. Convierte a minúsculas, separa los límites de camelCase y extrae tokens alfanuméricos. Por ejemplo, `SamplingParams` puede coincidir mediante los tokens `sampling` y `params`.

El estado preparado para la búsqueda contiene:

* entradas indexadas;

* tokens de cada fragmento;

* frecuencias de términos de cada fragmento;

* frecuencia documental de cada término;

* tokens de la consulta;

* longitud media de los fragmentos.

La longitud media se calcula una sola vez durante `prepare()`, en lugar de hacerlo para cada fragmento puntuado. Las búsquedas sobre datasets preparan el índice una vez y lo reutilizan para todas las preguntas.

Los resultados se ordenan por puntuación BM25 descendente. Solo se devuelven fragmentos con puntuación positiva. La ordenación estable de Python conserva el orden del índice en caso de empate, por lo que el resultado es determinista para la misma consulta y el mismo índice.

Para los datasets de código se utiliza `index_py.json` y para los datasets de documentación `index_md.json` cuando esos índices existen. Si el índice seleccionado no devuelve resultados, existe un fallback que busca en todos los índices disponibles.

## Archivos generados

### Índices JSON

```text
data/processed/index_py.json
data/processed/index_md.json
```

Cada entrada guarda la ruta de origen, el rango de caracteres y el texto extraído:

```json
{
  "file_path": "data/raw/vllm-0.10.1/vllm/sampling_params.py",
  "first_character_index": 3571,
  "last_character_index": 5547,
  "text": "..."
}
```

Se utiliza JSON porque es legible, fácil de inspeccionar y compatible con el flujo de evaluación.

### Caché de preparación BM25

```text
data/processed/cache/search_cache_py.pkl
data/processed/cache/search_cache_md.pkl
data/processed/cache/search_cache_all.pkl
```

La caché guarda el estado preparado de Python: tokens, frecuencias de términos, frecuencias documentales y longitud media. Es una caché del índice preparado, no una caché de resultados de consultas individuales.

La caché almacena una huella basada en la ruta del índice, el tamaño del archivo y la fecha de modificación. Si el índice cambia, la caché se ignora y se recalcula.

### Manifest de indexación incremental

```text
data/processed/manifest_index.json
```

El manifest almacena el tamaño de chunk configurado y una huella de contenido SHA-256 por archivo indexado. SHA-256 es un hash unidireccional, no cifrado ni un mecanismo de clave secreta. Se utiliza únicamente para detectar cambios.

Los archivos se clasifican como sin cambios, modificados, nuevos o eliminados. Los fragmentos sin cambios se reutilizan, mientras que los archivos nuevos o modificados se vuelven a dividir. Cambiar el tamaño máximo de chunk provoca una reconstrucción completa.

## Modelos de datos

Los principales modelos Pydantic son:

| Modelo | Propósito |
| --- | --- |
| `MinimalSource` | Ruta de origen y rango de caracteres. |
| `UnansweredQuestion` | Pregunta con identificador. |
| `AnsweredQuestion` | Pregunta, fuentes y respuesta generada. |
| `RagDataset` | Dataset que contiene `rag_questions`. |
| `MinimalSearchResults` | Pregunta y fuentes recuperadas. |
| `MinimalAnswer` | Resultados de búsqueda más una respuesta. |
| `StudentSearchResults` | Salida de búsqueda del estudiante más `k`. |
| `StudentSearchResultsAndAnswer` | Salida de respuestas más `k`. |

Los datasets, los resultados de búsqueda, las respuestas generadas y las peticiones de la API se validan con Pydantic. Los índices internos se cargan como entradas JSON porque contienen los datos serializados de los fragmentos que utiliza el buscador.

## Referencia de comandos

Todos los comandos deben ejecutarse mediante el Makefile:

```text
make run -- <comando> [opciones]
```

| Comando | Propósito |
| --- | --- |
| `index` | Construir o actualizar los índices del código fuente. |
| `search` | Imprimir los top-k fragmentos para una consulta. |
| `search_dataset` | Buscar todas las preguntas de un dataset y guardar los resultados JSON. |
| `answer` | Recuperar fuentes y generar una respuesta individual. |
| `answer_dataset` | Generar respuestas a partir de un JSON de resultados de búsqueda existente. |
| `evaluate` | Calcular Recall@k frente a un dataset de referencia. |
| `serve` | Iniciar la API HTTP local opcional. |

### `index`

```bash
make run -- index
make run -- index --max_chunk_size 1500
```

Recorre `data/raw/vllm-0.10.1/`, indexa los archivos `.py` y `.md` y escribe los resultados en `data/processed/`. Si no han cambiado ni el corpus ni la configuración, las ejecuciones posteriores reutilizan el índice existente.

### `search`

```bash
make run -- search '"How is the KV cache managed?" --k 5'
```

Está pensado para inspección interactiva e imprime en la terminal las rutas y los rangos de caracteres. No crea un fichero de resultados de dataset.

### `search_dataset`

```bash
make run -- search_dataset \\
  --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json \\
  --k 5 \\
  --save_directory data/output/search_results/UnansweredQuestions
```

Guarda un JSON `StudentSearchResults` con el mismo nombre que el dataset de entrada. La carpeta de salida debe ser diferente de la carpeta del dataset de entrada. Si el fichero ya existe, el programa solicita confirmación antes de sobrescribirlo.

### `answer`

```bash
make run -- 'answer "What is the purpose of the scheduler?" --k 5'
```

Imprime un `AnsweredQuestion` que contiene la pregunta, las fuentes recuperadas y la respuesta generada. Qwen solo se carga cuando existe contexto relevante.

### `answer_dataset`

```bash
make run -- answer_dataset \\
  --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \\
  --save_directory data/output/search_results_and_answer/UnansweredQuestions
```

No vuelve a realizar la recuperación. Lee el `StudentSearchResults` existente, reconstruye los contextos a partir de las fuentes guardadas y genera las respuestas por lotes. Si el fichero de salida ya existe, el programa solicita confirmación antes de sobrescribirlo.

### `evaluate`

```bash
make run -- evaluate \\
  --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \\
  --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json
```

Para que una fuente recuperada sea correcta, la ruta debe coincidir exactamente y los rangos de caracteres deben tener un Intersection over Union de al menos 0,05.

$\
$

El recall de cada pregunta es la proporción de fuentes de referencia recuperadas. El Recall@k global es la media de los recalls individuales.

## Análisis del rendimiento

Los siguientes valores se midieron con `k = 5` y la moulinette oficial el 24 de septiembre de 2026:

| Dataset | Recall@5 requerido | Recall@5 medido | Estado |
| --- | --- | --- | --- |
| `docs_public` | 0.80 | 0.8600 | Aprobado |
| `docs_private` | 0.80 | 0.8300 | Aprobado |
| `code_public` | 0.50 | 0.6465 | Aprobado |
| `code_private` | 0.50 | 0.5200 | Aprobado |

El resultado más cercano al mínimo es `code_private`, con 0.5200 frente al 0.50 requerido.

El proyecto también tiene como objetivo cumplir los límites de ejecución del enunciado:

* indexar completamente en menos de cinco minutos;

* procesar 200 preguntas en menos de 90 segundos.

En una ejecución, el procesamiento del dataset alcanzó aproximadamente 33 preguntas por segundo: 99 preguntas en aproximadamente 3,5 segundos. Los tiempos exactos dependen de la máquina y del entorno.

En la primera implementación, la longitud media de los fragmentos se recalculaba mientras se puntuaba cada fragmento. Esto generaba un coste cuadrático innecesario. Mover el cálculo a `prepare()` redujo la preparación medida de aproximadamente 5,5 segundos por consulta a aproximadamente 0,6 segundos, manteniendo la misma lógica de ranking. La caché de preparación evita repetir este trabajo en ejecuciones posteriores.

## Decisiones de diseño

* **BM25 implementado directamente:** permite controlar de forma transparente la puntuación, la tokenización, la caché y el orden determinista.

* **Índices JSON:** son legibles, fáciles de depurar y compatibles con el formato del proyecto.

* **Pickle para el estado BM25 preparado:** conserva eficientemente estructuras Python como `Counter`. Se usa únicamente para datos internos de caché.

* **Manifest SHA-256:** detecta cambios de contenido para la indexación incremental. Es un hash, no cifrado.

* **Índices separados por extensión:** permiten buscar código y documentación de forma independiente, reduciendo coincidencias irrelevantes.

* **Pydantic en los límites de datos:** valida datasets, ficheros de resultados, respuestas y peticiones API.

* **Herencia:** `SearchDataset` y `Answer` reutilizan la implementación común de búsqueda en lugar de duplicar la lógica BM25.

* **Generación determinista:** Qwen usa `do_sample=False` y la recuperación mantiene un orden estable en los empates.

* **Generación local:** el sistema utiliza `Qwen/Qwen3-0.6B` mediante `transformers` y no usa claves de API.

* **Ejecución mediante Makefile:** `make run` sincroniza las dependencias, ejecuta el comando con `uv` y realiza la limpieza posterior.

## Dificultades

| Dificultad | Solución |
| --- | --- |
| Recalcular la longitud media para cada fragmento puntuado | Calcularla una vez en `prepare()`. |
| Separadores irregulares de líneas en blanco | Usar una expresión regular que acepta varias líneas en blanco y espacios. |
| Reutilizar fragmentos durante la indexación incremental | Guardar huellas SHA-256 en `manifest_index.json`. |
| Distinguir rutas equivalentes como `data/output` y `./data/output` | Comparar las rutas resueltas. |
| Los booleanos de Python se comportan como enteros | Rechazarlos antes de validar enteros. |
| Los decimales pueden truncarse silenciosamente con `int()` | Rechazar floats no enteros antes de convertir. |
| Poco espacio en los ordenadores de 42 Madrid | Utilizar `set-local.sh` para dirigir entornos y cachés a `sgoinfre`. |

## Ejemplo de uso

Flujo completo:

```bash
make install
make run -- index

for d in docs_public docs_private code_public code_private; do
  make run -- search_dataset \\
    --dataset_path data/datasets/UnansweredQuestions/dataset_$d.json \\
    --k 5 \\
    --save_directory data/output/search_results/UnansweredQuestions
done

make run -- evaluate \\
  --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \\
  --dataset_path data/datasets/AnsweredQuestions/dataset_docs_public.json

make run -- answer_dataset \\
  --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \\
  --save_directory data/output/search_results_and_answer/UnansweredQuestions

make run -- answer "What is the purpose of the scheduler?" --k 5
make run -- serve
```

Una respuesta individual tiene esta estructura general:

```json
{
  "question": "What is the purpose of the scheduler?",
  "sources": [
    {
      "file_path": "data/raw/vllm-0.10.1/vllm/core/scheduler.py",
      "first_character_index": 1000,
      "last_character_index": 1800
    }
  ],
  "answer": "Respuesta generada a partir del contexto recuperado."
}
```

## Bonus

| Bonus | Estado | Descripción |
| --- | --- | --- |
| Indexación incremental | Implementado | Manifest SHA-256 y reutilización de fragmentos de archivos sin cambios. |
| Caché | Implementado | Caché de tokenización y estadísticas BM25; no se cachean consultas individuales. |
| API HTTP local | Implementado | Endpoints FastAPI para búsqueda y respuesta. |
| Embeddings semánticos | No implementado | — |
| Recuperación híbrida | No implementado | — |

Los tres bonus implementados siguen la misma idea: no repetir un trabajo que ya está hecho. La indexación incremental evita reindexar archivos que no han cambiado, la caché evita volver a preparar un índice que ya está preparado y la API reutiliza las mismas clases que la línea de comandos en lugar de duplicar la lógica.

### Indexación incremental

La pregunta que resuelve es: ¿por qué trocear de nuevo todos los archivos de vLLM si solo ha cambiado uno? `Index.update_index()` en `index.py` lo evita así:

1. Al empezar, calcula el SHA-256 del contenido de cada archivo compatible (`_file_fingerprint` lee los bytes y los hashea).

2. Carga el `manifest_index.json` de la ejecución anterior, que guardó esas huellas junto con el `max_chunk_size` utilizado.

3. Compara ambas listas en `_classify_files` y clasifica cada archivo como sin cambios, modificado, nuevo o eliminado. Si el `max_chunk_size` cambió, marca todos los archivos para forzar una reconstrucción completa.

4. Si no hay archivos nuevos, modificados ni eliminados, informa de que el índice está actualizado y termina sin tocar nada.

5. Los archivos sin cambios aportan sus fragmentos tal cual: se toman de los JSON de índice existentes filtrando por su ruta.

6. Solo los archivos nuevos y modificados se leen y se vuelven a trocear con `Chunker`, y sus fragmentos se añaden a los conservados.

7. Se reescriben los índices por extensión con el resultado combinado y se guarda el manifest con las huellas actuales, para que la siguiente ejecución compare contra él.

```bash
make run -- index
```

La segunda ejecución puede indicar que el índice está actualizado si no ha cambiado ningún archivo compatible.

### Caché de búsqueda

La parte cara de una búsqueda no es puntuar con BM25, sino preparar el índice: tokenizar todos los fragmentos, contar sus frecuencias y calcular la longitud media. Ese trabajo solo depende del índice, no de la pregunta, así que solo se hace una vez. `Search.prepare()` en `search.py` lo gestiona así:

1. `prepare()` carga el JSON, tokeniza la consulta y llama a `_load_cache` antes de hacer nada más.

2. La caché es un Pickle por índice (`search_cache_py.pkl`, `search_cache_md.pkl` o `search_cache_all.pkl`) dentro de `data/processed/cache/`.

3. Cada Pickle guarda los tokens de cada fragmento, sus frecuencias de término, las frecuencias documentales, la longitud media y una huella de los ficheros de índice (ruta, tamaño y fecha de modificación).

4. Al cargar, compara la huella guardada con la actual: si coincide, reutiliza todos los datos y se salta la tokenización; si no coincide, o el Pickle no se puede leer, recalcula todo y guarda la caché de nuevo.

5. Lo que se cachea es el estado preparado del índice, nunca el resultado de una consulta concreta. Así, en un dataset el índice se prepara una vez y todas las preguntas lo reutilizan.

### API HTTP

La API expone la búsqueda y las respuestas por HTTP reutilizando las clases `Search` y `Answer` de la línea de comandos. En `api.py`, la clase `RagApi` crea la aplicación FastAPI y registra los endpoints:

* `POST /search` recibe un cuerpo Pydantic `SearchRequest` con `{"query": "...", "k": 5}`, valida que la consulta no esté vacía y que `k` sea positivo (HTTP 400 en caso contrario), ejecuta `Search.prepare()` aprovechando la caché y devuelve una lista de objetos `MinimalSource`.

* `POST /answer` con el mismo cuerpo construye el contexto con `Answer`; si no hay fuentes recuperadas devuelve HTTP 404 y, si las hay, construye el prompt, genera la respuesta con Qwen y devuelve un `AnsweredQuestion`.

* `/docs` ofrece la documentación automática de FastAPI.

Iniciar la API:

```bash
make run -- serve
```

## Limitaciones conocidas

* La recuperación es léxica. Una pregunta muy parafraseada y sin términos compartidos puede no recuperar la fuente correcta.

* Qwen/Qwen3-0.6B es un modelo local pequeño, por lo que las respuestas pueden ser incompletas aunque la recuperación sea correcta.

* El solapamiento repite una pequeña cantidad de texto entre fragmentos vecinos, aunque cada fragmento almacenado respeta el tamaño máximo configurado.

* Actualmente el proyecto utiliza Qwen/Qwen3-0.6B como modelo de generación.

Como mejoras futuras se podrían incorporar embeddings semánticos con un modelo ligero y un ranker híbrido que combinase recuperación léxica y semántica.

## Recursos y uso de IA

### Referencias técnicas

El algoritmo de recuperación y el flujo RAG implementados se basan en técnicas documentadas en:

* Lewis et al., _Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks_ (2020): [https://arxiv.org/abs/2005.11401](https://arxiv.org/abs/2005.11401)

* Robertson y Zaragoza, _The Probabilistic Relevance Framework: BM25 and Beyond_ (2009): [https://doi.org/10.1561/15000019](https://doi.org/10.1561/15000019)

* Manning, Raghavan y Schütze, _Introduction to Information Retrieval_: [https://nlp.stanford.edu/IR-book/](https://nlp.stanford.edu/IR-book/)

Estos originales no se consultaron directamente durante el desarrollo. Se citan como referencia de lo implementado; la explicación de las técnicas se trabajó mediante la asistencia de IA descrita más abajo.

### Herramientas y dependencias

Enlaces a la documentación de las herramientas que utiliza el código:

* Documentación de vLLM: [https://docs.vllm.ai](https://docs.vllm.ai)

* Qwen/Qwen3-0.6B: [https://huggingface.co/Qwen/Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B)

* Pipelines de Hugging Face Transformers: [https://huggingface.co/docs/transformers/main_classes/pipelines](https://huggingface.co/docs/transformers/main_classes/pipelines)

* Documentación de Pydantic: [https://docs.pydantic.dev](https://docs.pydantic.dev)

* Python Fire: [https://github.com/google/python-fire](https://github.com/google/python-fire)

* Documentación de uv: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

* Documentación de FastAPI: [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)

El corpus es el repositorio público de vLLM 0.10.1. Los datasets públicos y privados y la moulinette son materiales proporcionados por 42.

### Uso de IA

La IA se utilizó como herramienta de aprendizaje y apoyo, no como sustituto de la comprensión. Se utilizó para:

* explicar RAG, BM25, `transformers` y el flujo de generación;

* identificar y explicar el cálculo cuadrático de la longitud media;

* revisar la validación de entradas y los casos límite;

* comparar la implementación con los requisitos del enunciado;

* ayudar a estructurar y documentar el proyecto.

Las decisiones de diseño, la implementación, las pruebas y las mediciones de rendimiento fueron revisadas y comprendidas antes de incluirlas en el proyecto.

<br>

## Fundación Telefónica

Para ejecutar el programa en los ordenadores de la Fundación Telefónica, crea un script que dirija las cachés y el entorno a `goinfre`. No utilices `sgoinfre`.

Puedes comprobar la ubicación actual de la caché con:

```bash
uv cache dir
```

### Configuración del entorno local

1. Crea un archivo llamado `set-local.sh`.

2. Escribe y guarda el siguiente contenido:

```bash
export CALLME_STORAGE="/home/aitorres/goinfre/RAG"

export UV_CACHE_DIR="$CALLME_STORAGE/uv-cache"
export UV_PROJECT_ENVIRONMENT="$CALLME_STORAGE/venv"
export UV_PYTHON_INSTALL_DIR="$CALLME_STORAGE/python"

export HF_HOME="$CALLME_STORAGE/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub"

export TMPDIR="$CALLME_STORAGE/tmp"
export XDG_CACHE_HOME="$CALLME_STORAGE/xdg-cache"
```

1. Ejecuta el script con `source`:

```bash
source set-local.sh
```

1. Comprueba de nuevo la ubicación de la caché:

```bash
uv cache dir
```

La ruta mostrada debe apuntar a `goinfre`. De esta forma, `uv` y las demás herramientas pueden instalar y guardar sus dependencias fuera del espacio limitado de la máquina.

<br>

## Ejecución del proyecto con la moulinette

### Evaluación de recuperación

1. Crea tu carpeta principal `RAG`.

2. En la raíz, crea una carpeta `student` y copia dentro el repositorio. Debe contener `data/datasets` y `data/raw/vllm-0.10.1`.

3. En la raíz, crea la carpeta `data` y dentro de ella `datasets`. Dentro de `datasets`, pega `private` y su contenido a partir del archivo `datasets_private.zip`.

4. En la raíz, coloca `exams.zip` y `moulinette.zip`. Después, descomprime `unzip exams.zip` y `unzip moulinette.zip`.

5. Ejecuta:

```bash
./exams/scripts/exam_retrieval.sh --student-path ./student --moulinette-path ./moulinette-ubuntu
```

1. Se generará un test de cuatro fases. Al finalizar, se mostrará `STATUS: PASS` si todo es correcto.

### Corrección: Answer Quality

```bash
./exams/scripts/exam_answer.sh \
--student-path ./student \
--moulinette-path ./moulinette-ubuntu
```

1. Ejecuta el comando en la raíz.

2. Espera hasta la fase 2, `questions`.

3. Elige tres preguntas marcadas como `VALID` y envíalas una a una.

4. Genera las tres respuestas mediante `answer`.

5. Finaliza con el resumen de la evaluación.

### System Reliability

```bash
./exams/scripts/exam_edge_cases.sh --student-path ./student
```

Ejecuta distintos tests de casos límite. Si todo es correcto, el resultado final será:

```text
====
 FINAL RESULT: 4/4
====
Results saved to: /home/aitorres/42madrid/****/evaluations/edge_cases/2026-09-29_01-35-40
STATUS: PASS
```