from math import ceil
from multiprocessing import Process
from typing import List, Tuple, Dict, Union
from colorama import Fore, Style, init

from metodos import file_lines_pos, compile_words_regex, total, process_files, print_results, chunks

init() # Inicialização colorama

### Helpers

# TRAB2
# fazer o offset, yield das proximas linhas
# read_line() para consumir a linha só se não for 0
# confirmar que não é preciso mais seeks

### Parsing

def main():
    """
    Processa e divide a pesquisa/contagem de ficheiros por processos (se aplicável).
    """
    # args = parse()

    # Debug ----
    args = {
        'palavras': ['batatas', 'milho', 'antonio'],
        'all': False,
        'count': True,
        'files': ['file0.txt', 'file0_0.txt'],
        'parallelization': 2
    }
    # ----------

    words = compile_words_regex(args['palavras'])
    for i in range(len(words)):
        total[i] = 0

    # O pai faz a pesquisa e contagem quando parallelization é 0
    if args['parallelization'] == 0:
        process_files(args['files'], words, args['all'], args['count'])
    else:
        files = [(path, *file_lines_pos(path)) for path in args['files']]
        total_lines = sum(f[1] for f in files)
        # chunks(files, total_lines, args['parallelization'])
        children_files = list(chunks(files, total_lines, args['parallelization']))

        processos = []
        for child_files in children_files:
            processos.append( Process(target=process_files, args=(child_files, words, args['all'], args['count'])) )

        for i in processos:
            i.start()
        for i in processos:
            i.join()


    # Imprimir total dos resultados
    if len(args['files']) > 1:
        print(f'{Fore.LIGHTRED_EX}Total:{Style.RESET_ALL}')
        # A partir do Python 3.7 os dicionários são ordenados, portanto pode-se usar a lista inicial das palavras
        print_results(args['palavras'], args['all'], args['count'])

if __name__ == '__main__':
    try:
        main()
        pass
    except UserWarning as w:
        print(w)
