from itertools import groupby
from time import time, sleep
from os import getpid
from pickle import dump
from typing import List, Generator, Dict, Union, Tuple, Pattern
from multiprocessing import Process, Value, Array, Lock, Pipe, current_process
from math import ceil
from re import findall, compile
from argparse import ArgumentParser
from unicodedata import category, normalize
from signal import signal, SIGINT
from threading import Thread

from colorama import Fore, Style, init
init() # Inicialização colorama

# Transforma segundos em microsegundos
to_micro = lambda s: int(s * 1000000)

stop = False
dic_files_total = {}
""" dic_files_total
    Chave: caminho ficheiro
    Value: quantidade de processos que o processam
"""

dic_files_done = {}
""" dic_files_done
    Chave: pid
    Valor: List
        Valor: Dict
            { pid: int,
              file: Dict
                { path: str,
                  start: int,
                  end: int,
                  lines: int },
              duration: float }
"""

mutex = Lock()
pipe_pai,pipe_filho = Pipe()
total = Array('i', 3) # Inicialização do contador global das palavras (máx. 3 palavras)
children_active = Value("i", 0)

# Inicio execução
inicio_execucao = time()

def chunks(files: List[Tuple[str, int, List[int]]], total_lines: int, n: int) -> List[List[Dict[str, Union[str, int]]]]:
    """
    Separa ficheiros em n parcelas equitativamente

    :param files: Lista de tuplos em que a primeira posição representa o caminho do ficheiro, a segunda a quantidade de linhas, e a última a lista de posições do inicio da linha i
    :param total_lines: Quantidade total de linhas
    :param n: Quantidade de parcelas a dividir
    :return: Lista das n parcelas
            A lista interior representa j ficheiros na parcela i
            A lista mais interior representa o caminho do ficheiro, a posição em que irá começar, a posição em que irá acabar, e as quntidade de linhas desta divisão
    """
    file_idx = 0
    file_lines = 0

    lines_each = ceil(total_lines / n)

    res = [
        [ { 'path': files[file_idx][0],
              'start': 0,
              'end': files[file_idx][2][-1],
              'lines': 0 } ]
    ]
    """
    [
        [ processo_i
            { ficheiro_j
                path: str, start: int, end: int, lines: int 
            }
        ]
    ]
    """

    # Enquanto o ficheiro não tiver sido totalmente atribuido
    while file_idx < len(files) and file_lines < files[file_idx][1]:
        to_add = min(lines_each, files[file_idx][1] - file_lines)

        file_lines += to_add
        res[-1][-1]['lines'] += to_add

        eof = file_lines >= files[file_idx][1]
        if not eof:
            res[-1][-1]['end'] = files[file_idx][2][file_lines]

        next_process = res[-1][-1]['lines'] >= lines_each
        # Passar ao próximo ficheiro
        if eof:
            file_lines = 0
            file_idx += 1
            if not next_process and file_idx < len(files):
                res[-1].append(
                    { 'path': files[file_idx][0],
                      'start': 0,
                      'end': files[file_idx][2][-1],
                      'lines': 0 } )

        # Passar ao próximo processo
        if next_process and file_idx < len(files):
            res.append(
                [
                    {'path': files[file_idx][0],
                     'start': files[file_idx][2][file_lines],
                     'end': files[file_idx][2][-1],
                     'lines': 0 }
                ]
            )

    return res

def read_list(text: str) -> List[str]:
    """
    Lê e divide uma linha do stdin.
    :param text: String com a mensagem a mostrar ao utilizador.
    :return: Lista de Strings com os elementos da linha.
    """
    inp = input(text)
    files = inp

    # Enquanto a linha não for vazia lê mais valores
    while inp:
        inp = input()
        files += f' {inp}'

    # Partir os valores pelo espaço
    return files.split()

def file_lines_pos(path: str) -> Tuple[int, List[int]]:
    """
    Em que posição começa a linha i
    :param path: Caminho do ficheiro
    :return: Lista das posições do início da linha i do ficheiro
    """
    line_offset = []
    offset = 0

    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line_offset.append(offset)
                offset += len(line)
    except Exception as err:
        print(f'{Fore.LIGHTRED_EX}Ficheiro {path}: {err}{Fore.RESET}')

    return len(line_offset), line_offset

def strip_accents(s: str) -> str:
    """
    Remove acentos e outros caracteres (diacríticos) da string s.

    :param s: String a remover os caracteres.
    :return: String sem os caracteres.
    """
    return ''.join(c for c in normalize('NFD', s)
                  if category(c) != 'Mn')

def read_file(file: Dict[str, Union[str, int]]) -> Generator[str, None, None]:
    """
    Lê um ficheiro do caminho file['path'] começando em file['start'] e acabando em file['end']

    :param file: Dicionário com o path, o start e o end de um ficheiro
    :return: Gerador das linhas do ficheiro.
    """
    offset = file['start']
    with open(file['path'], 'r', encoding='utf-8') as f:
        try:
            while True:
                # tem fim e chega a esse fim
                if offset > file['end']:
                    break

                f.seek(offset, 0)
                line = f.readline()
                if line:
                    offset += len(line)
                    yield line
                else:
                    break
        except Exception as err:
            f.seek(f.tell()+1, 0)

def parse() -> Dict[str, Union[str, int, bool, Tuple[str]]]:
    """
    Define o parser de argumentos.
    :return: Dict com valores dos argumentos escolhidos pelo utilizador.
    """
    parser = ArgumentParser(description='Pesquisa até três palavras em pelo menos um ficheiro, \
                                            devolvendo as linhas que contêm unicamente uma das \
                                            ou todas as palavras. Conta e pesquisa paralelamente \
                                            os números de ocorrências de cada palavra e de linhas \
                                            devolvidas de cada/todas as palavra(s), devolvendo-os.')

    mutually_exclusive = parser.add_mutually_exclusive_group(required=True)

    parser.add_argument('-a', '--all', action='store_true',
                        help='Opção que define se o comando pesquisa as linhas de texto que contêm \
                            unicamente uma das palavras ou todas as palavras. Por omissão, pesquisa \
                            as linhas contendo unicamente uma das palavras.')

    mutually_exclusive.add_argument('-c', '--count', action='store_true',
                                    help='Opção que obtém o número de ocorrências das palavras a pesquisar.')

    mutually_exclusive.add_argument('-l', '--lines', action='store_true',
                                    help='Opção que permite obter o número de linhas devolvidas. \
                                        Caso a opção -a não esteja ativa, o número de linhas \
                                        devolvido é por palavra.')

    parser.add_argument('-p', '--parallelization', type=int, default=0,
                        help='Opção que permite definir o nível de paralelização n do comando. \
                            Por omissão, não há paralelização.')

    parser.add_argument('palavras', nargs='+',
                        help='As palavras a pesquisar no conteúdo dos ficheiros. \
                            Máximo 3 palavras.')

    parser.add_argument('-f', '--files', nargs='+',
                        help='Ficheiro(s), sobre o(s) qual(is) é efetuada a pesquisa e contagem. \
                            Por omissão, o comando pede o(s) ficheiro(s) ao utilizador.')

    parser.add_argument('-w', '--interval', type=int, default=0,
                        help='Define o intervalo de tempo s em que o estado da contagem de \
                             linhas ou ocorrências é escrito.')

    parser.add_argument('-o', '--output', type=str,
                        help='Define o ficheiro file que guarda o histórico da execução do programa em binário.')

    args = parser.parse_args().__dict__

    # Args is passed as reference!!
    validate_args(args)

    return args

def validate_args(args: Dict[str, Union[str, int, bool, List[str]]]) -> None:
    """
    Valida argumentos e remove duplicados.
    :param args: Dicionário com argumentos por validar.
    """
    # Remover duplicados
    args['palavras'] = tuple(set(strip_accents(word) for word in args['palavras']))

    # Impor limites
    if len(args['palavras']) > 3:
        raise UserWarning('Argument palavras must not be longer than 3.')

    if args['parallelization'] < 0:
        raise UserWarning('Argument -p must not be smaller than 0.')

    # Obter ficheiros do stdin
    if args['files'] is None:
        args['files'] = read_list('Insira o(s) ficheiro(s) a pesquisar: ')

    # Impor limites
    args['files'] = tuple(set(args['files']))

    # Import limites do parallelization
    if args['parallelization'] > len(args['files']):
        raise UserWarning(f'Argument -p must not be greater than file count ({len(args["files"])}).')

def compile_words_regex(words: Tuple[str]) -> List[Tuple[str, Pattern]]:
    """
    Compila as palavras em expressões regulares para melhorar desempenho.

    :param words: Tuplo de Strings com palavras a compilar.
    :return: Lista de tuplos com par String palavra e a sua Pattern expressão regular.
    """
    # usar o compile da biblioteca re para melhor desempenho, ao invés de definir o regex das palavras em cada linha de cada ficheiro
    return [ (word, compile(f'\\b{word}\\b')) for word in words ]

def search_file(file: Dict[str, Union[str, int]], words: List[Tuple[str, Pattern]], all_words: bool) -> Dict[str, Dict[int, int]]:
    """
    Pesquisa e conta ocorrências de dada(s) palavra(s) num ficheiro.
    :param path: String com o caminho do ficheiro.
    :param words: Lista de tuplos com pares String palavra e a sua Pattern
                  expressão regular a pesquisar/contar.
    :param all_words: Bool cujo True representa se a pesquisa/contagem deve apenas
                      contabilizar linhas com todas as palavras dadas.
    :return: Dicionário com as ocorrências de cada palavra por linha.
    """
    # Dicionário das ocorrências das palavras em cada linha
    occurrences = { word: {} for word, _ in words }
    """ occurrences
        Chave: palavra
        Valor: Dict
                Chave: índice da linha
                Valor: Quantidade de ocorrências [da palavra] nessa linha
    """

    # For each line of file
    for i, line in enumerate(read_file(file)):
        # Remove diacritics
        normalized_line = strip_accents(line)

        # Dicionário das ocorrências das palavras na linha i
        line_word_occurrences = { word: 0 for word, _ in words }
        """ line_word_occurrences
            Chave: palavra
            Valor: Quantidade de ocorrências [da palavra] na linha i
        """

        for word, regex in words:
            # Guardar a quantidade de ocorrências da palavra word na linha i
            line_word_occurrences[word] = len(findall(regex, normalized_line))

        # Iterador em que o valor de cada palavra é boolean (se foi encontrada ou não na linha).
        diff_zero = [line_word_occurrences[word] != 0 for word in line_word_occurrences]
        it = iter(diff_zero)

        # Como é iterador, o any consome até ao primeiro True que encontra.
        # Logo, se consumimos o primeiro True e negamos o próximo, sabemos que só existe um.
        is_valid = any(it) and not any(it)

        # Sem o parâmetro -a, só pode haver uma palavra por linha, ou seja o valor de is_valid
        # Mas com o parâmetro -a, ou all_words no contexto da função, ativo, pode ser apenas uma palavra na linha ou todas as palavras nessa linha
        if all_words and not is_valid:
            # Assim, reescreve-se o valor de is_valid para que o seu significado seja se todas as palavras estão presentes na linha
            is_valid = all(diff_zero)

        # Após a validação do argumento -a, só se conta estas ocorrências se a validação tiver resultado positivo
        if is_valid:
            # Agora adiciona-se ao dicionário occurrences os resultados da linha atual, para cada palavra
            for word in line_word_occurrences:
                # só se insere se houver ocorrência(s) da palavra na linha
                if line_word_occurrences[word] != 0:
                    # i representa o índice da linha
                    occurrences[word][i] = line_word_occurrences[word]

    return occurrences

def print_results(words: List[str], all_words: bool, count: bool, val: List[str] = None) -> None:
    """
    Imprime resultados para o stdout.
    :param words: Lista de Strings com palavra(s).
    :param all_words: Bool cujo True representa se a pesquisa/contagem deve apenas
                      com todas as palavras dadas.
    :param count: Bool cujo True representa se é impressa a quantidade de ocorrências
                  e cujo False a quantidade de linhas.
    :param val?: Lista de Strings com valores a escrever. Quando especificado, sobrepõe-se aos valores totais
    """
    if count:
        for i, word in enumerate(words):
            # Somar todas as ocorrências de todas as
            print(f'\tA palavra {Fore.CYAN}{word}{Fore.RESET} ocorre {Fore.GREEN}{val[i] if val else total[i]}{Fore.RESET} vezes.')
    else:
        # Argumento -l
        if all_words:
            # numero de linhas devolvidas da pesquisa
            print(f'\t{Fore.GREEN}{val[0] if val else total[0]}{Fore.RESET} linhas respeitam a pesquisa.')
        else:
            # numero linhas devolvida é por palavra
            for i, word in enumerate(words):
                print(
                    f'\tA palavra {Fore.CYAN}{word}{Fore.RESET} ocorre em {Fore.GREEN}{val[i] if val else total[i]}{Fore.RESET} linhas.')

def commit_results(word_occurrences: Dict[str, Dict[int, int]], all_words: bool, count: bool) -> List[int]:
    """
    Mapeia as ocorrências dependendo dos argumentos do utilizador e incrementa os resultados globais.

    :param word_occurrences: Dicionário com as ocorrências das palavras em cada linha.
    :param all_words: Bool cujo True representa se a pesquisa/contagem deve apenas
                      com todas as palavras dadas.
    :param count: Bool cujo True representa se é impressa a quantidade de ocorrências
                  e cujo False a quantidade de linhas.
    :return: Ocorrências mapeadas
    """
    ret = []
    # Argumento -c
    if count:
        for i, word in enumerate(word_occurrences):
            # Somar todas as ocorrências de todas as
            val = sum(word_occurrences[word][k] for k in word_occurrences[word])
            ret.append(val)
            mutex.acquire()
            total[i] += val
            mutex.release()
    else:
        # Argumento -l
        if all_words:
            # numero de linhas devolvidas da pesquisa
            val = len(set(key for word in word_occurrences for key in word_occurrences[word].keys()))
            ret.append(val)
            mutex.acquire()
            total[0] += val
            mutex.release()
        else:
            # numero linhas devolvida é por palavra
            for i, word in enumerate(word_occurrences):
                val = len(word_occurrences[word])
                ret.append(val)
                mutex.acquire()
                total[i] += val
                mutex.release()
    return ret

def process_files(files: List[Dict[str, Union[str, int]]], words: List[Tuple[str, Pattern]], all_words: bool, count: bool) -> None:
    """
    Processa e imprime resultados da pesquisa/contagem de dadas palavras em dados ficheiros.
    :param files: Lista de Strings com o caminho dos ficheiros.
    :param words: Lista de tuplos com pares String palavra e a sua Pattern
                  expressão regular a pesquisar/contar.
    :param all_words: Bool cujo True representa se a pesquisa/contagem deve apenas
                      com todas as palavras dadas.
    :param count: Bool cujo True representa se é impressa a quantidade de ocorrências
                  e cujo False a quantidade de linhas.
    """
    for file in files:
        inicio = time()

        # Pesquisar e contar as palavras
        word_occurrences = search_file(file, words, all_words)
        # Processar e guardar os resultados no Array total
        vals = commit_results(word_occurrences, all_words, count)

        # Imprimir resultados
        mutex.acquire()
        print(f'{Fore.LIGHTMAGENTA_EX}Ficheiro {file["path"]}:{Style.RESET_ALL}')
        print_results(word_occurrences.keys(), all_words, count, vals)
        mutex.release()

        dados = {
            'pid': getpid(),
            'file': file,
            'duration': time() - inicio,
            'occurrences': vals
        }

        if current_process().name == 'MainProcess':
            put_files_done(dados)
        else:
            pipe_filho.send(dados)

        if stop:
            break

    children_active.value -= 1

def sigint(_sig, _null) -> None:
    """
    Altera a variável 'stop' para 'True' para assim parar o processamento de outros ficheiros
    :param _sig: obrigatório pelo signal
    :param _null: obrigatório pelo signal
    """
    global stop

    stop = True

def interval(interval: int, words: List[str], all_words: bool) -> None:
    """
    Imprime os resultados até ao momento, a cada interval segundos
    :param interval: Intervalo em segundos
    """

    qtty_total = len(dic_files_total)
    while children_active.value > 0:
        dic_done = {k: 0 for k in dic_files_total }
        occurrences = [0, 0, 0]
        for p in dic_files_done:
            for f in dic_files_done[p]:
                dic_done[f['file']['path']] += 1
                occurrences = [a + b for a, b in zip(occurrences, f['occurrences'])]


        remaining = set()
        for k in dic_done:
            if dic_files_total[k] != dic_done[k]:
                remaining.add(k)

        qtty_remaining = len(remaining)
        taken = to_micro(time()-inicio_execucao)
        len_taken = len(str(taken)) + 2

        res = [ f'{Fore.RESET}Ficheiros completamente processados: {Fore.LIGHTBLACK_EX}..................{"." * (len_taken - len(str(qtty_total - qtty_remaining)))} {Fore.LIGHTGREEN_EX}{qtty_total - qtty_remaining}',
                f'{Fore.RESET}Ficheiros em processamento: {Fore.LIGHTBLACK_EX}...........................{"." * (len_taken - len(str(qtty_remaining)))} {Fore.LIGHTGREEN_EX}{qtty_remaining}',
                f'{Fore.RESET}Tempo decorrido desde o início da execução do programa: {Fore.LIGHTGREEN_EX}{taken}µs' ]

        for i, word in enumerate(words):
            res.append(f'{Fore.RESET}Frequência da palavra {word} {Fore.LIGHTBLACK_EX}{"." * (32 + len_taken - len(word) - len(str(occurrences[i])))} {Fore.LIGHTGREEN_EX}{occurrences[i]}')

        print('\n' + '\n'.join(res) + '\n')

        sleep(interval)

def put_files_done(dados) -> None:
    """
    Adiciona ao dicionário 'dic_files_done', na chave do pid do processo que acabou o processamento, de um dado ficheiro
    :param dados: Dados relativos ao processamento do ficheiro
    """
    if dados['pid'] not in dic_files_done:
        dic_files_done[dados['pid']] = []
    dic_files_done[dados['pid']].append(dados)

def get_children_data() -> None:
    """
    Mensagens que o processo pai recebe e sobre o ficheiro processado por um filho
    """
    while children_active.value > 0:
        dados = pipe_pai.recv()
        put_files_done(dados)

def map_files(paths: List[str], parallelization: int) -> List[List[Dict[str, Union[str, int]]]]:
    global dic_files_total
    files = [x for x in ((path, *file_lines_pos(path)) for path in paths) if x[1]]
    total_lines = sum(f[1] for f in files)

    chunked_files = chunks(files, total_lines, parallelization)

    # Atualizar o dic_files_total com os
    flat_files_total = [item for sublist in chunked_files for item in sublist]
    sorted_files_total = sorted(flat_files_total, key=lambda x: x['path'])
    groupped_files_total = groupby(sorted_files_total, key=lambda x: x['path'])
    dic_files_total = {}
    for f in groupped_files_total:
        dic_files_total[f[0]] = len(list(f[1]))

    return chunked_files

def init_threads(_interval: int = None, words: List[str] = None, all_words: bool = None, parallelization: int = None) -> None:
    """
    Inicia as threads de contagem de impressão ou receção de resultados
    :param _interval: Intervalo de impressão de resultados
    :param parallelization: Quantidade de processos filhos
    :return:
    """
    # Thread de mostrar os resultados a cada interval segundos
    if _interval:
        thread_interval = Thread(target=interval, args=(_interval, words, all_words))
        thread_interval.start()

    # Thread de receber os dados dos filhos
    if parallelization:
        thread_data = Thread(target=get_children_data)
        thread_data.start()

def main() -> None:
    """
    Processa e divide a pesquisa/contagem de ficheiros por processos (se aplicável).
    """
    global dic_files_total

    # Prod -----
    args = parse()
    # ----------

    # Debug ----
    # args = {
    #     'palavras': ['batatas', 'milho', 'antonio'],
    #     'all': False,
    #     'count': True,
    #     'files': ['.gitignore', 'batatafrita.bin', 'batatafrita.txt', 'fgrande.txt', 'file0.txt', 'file0_0.txt', 'file0_1.txt', 'file0_2.txt', 'file2.bin', 'gerar_ficheiro.py', 'hpgrepwc.py', 'old_pgrepwc.py', 'pgrepwc.py', 'README.txt'],
    #     'parallelization': 1,
    #     'output': 'batatafrita.bin',
    #     'interval': 1
    # }
    # ----------

    # Quando o SIGINT (CTRL+C) é pressionado
    signal(SIGINT, sigint)

    children_active.value = args['parallelization']
    words = compile_words_regex(args['palavras'])
    for i in range(len(words)):
        total[i] = 0

    # Indexar
    print(f'{Fore.LIGHTBLACK_EX}Indexing...{Style.RESET_ALL}')
    files = map_files(args['files'], max(args['parallelization'], 1))

    init_threads(args['interval'], args['palavras'], args['all'], args['parallelization'])

    # Pesquisar
    print(f'{Fore.LIGHTBLACK_EX}Searching...{Style.RESET_ALL}')
    # O pai faz a pesquisa e contagem quando parallelization é 0
    if not args['parallelization']:
        process_files(files[0], words, args['all'], args['count'])
    else:
        processos = []
        for child_files in files:
            processos.append( Process(target=process_files, args=(child_files, words, args['all'], args['count'])) )

        for i in processos:
            i.start()
        for i in processos:
            i.join()

    # A partir daqui os filhos estão todos mortos
    # Imprimir total dos resultados
    if len(args['files']) > 1:
        print(f'{Fore.LIGHTRED_EX}Total{" até ao momento" if stop else ""}:{Style.RESET_ALL}')
        # A partir do Python 3.7 os dicionários são ordenados, portanto pode-se usar a lista inicial das palavras
        print_results(args['palavras'], args['all'], args['count'])

    # Escrever para fichiro binário
    if args['output']:
        output(args['output'],
               to_micro(inicio_execucao),
               to_micro(time()-inicio_execucao),
               args['parallelization'],
               args['all'],
               args['count'],
               args['interval'])

def output(path: str, start: int, duration: int, parallelization: int, all_words: bool, count: int, _interval: int) -> None:
    """
    Escrever os resultados de execução para um ficheiro binário
    :param path: Caminho do ficheiro onde escrever
    :param words: Palavras pesquisadas
    :param start: UNIX timestamp do início de execução
    :param duration: Duração de execução em µs
    :param parallelization: Quantidade de processos filhos (0 se tiver sido apenas o pai)
    :param all_words: Se a opção -a está ativa
    :param count: Se a opção -c está ativa
    :param interval: Intervalo de escrita de mensagens
    """
    out = {
        'start': start,
        'duration': duration,
        'children': parallelization,
        'all': all_words,
        'count': count,
        'interval': _interval,
        'processes': []
    }

    for p_files in dic_files_done:
        process = {
            'pid': p_files,
            'files': []
        }

        for f in dic_files_done[p_files]:
            process['files'].append({
                'path': f['file']['path'],
                'duration': to_micro(f['duration']),
                'lines': f['file']['lines'],
                'occurrences': f['occurrences']
            })
        out['processes'].append(process)

    with open(path, 'wb') as file:
        dump(out, file)

if __name__ == '__main__':
    try:
        main()
    except UserWarning as w:
        print(w)
