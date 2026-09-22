from .search import Search


class SearchDataset(Search):
    def __init__(self, dataset_path, k):   # valida y lee el JSON, extrae preguntas
        pass
    def run(self):                          # prepare() 1 vez → bucle → search(pregunta)
        pass                                    # → construye StudentSearchResults → guarda