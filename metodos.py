
from typing import List, Generator, Dict, Union, Tuple, Pattern

from math import ceil
from colorama import Fore, Style
from re import findall, compile
from argparse import ArgumentParser
from unicodedata import category, normalize
from multiprocessing import Array, Lock

mutex = Lock()
total = Array("i", 3) # Inicialização do contador global das palavras (máx. 3 palavras)

# Ficheiro com métodos partilhados pelos ficheiros do projeto

def chunks(files: List[Tuple[str, int, List[int]]], total_lines: int, n: int) -> List[List[Dict[str, Union[str, int]]]]:
    """
    Gera dado número de combinações de elementos de uma lista.

    :param files: Lista de tuplos em que a primeira posição representa o caminho do ficheiro, a segunda a quantidade de linhas, e a última a lista de posições do inicio da linha i
    :param total_lines: Quantidade total de linhas
    :param n: Paralelizaçõo
    :return: Lista do que cada processo deve processar.
            A lista interior representa j ficheiros a processar pelo processo i
            A lista mais interior representa o caminho do ficheiro, a posição em que irá começar e a posição em que irá acabar (se esta for -1, é até ao fim)
    """
    file_idx = 0
    file_lines = 0

    lines_each = ceil(total_lines / n)
    current_lines = 0

    res = [
        [
            { 'path': files[file_idx][0],
              'start': 0,
              'end': -1 }
        ]
    ]
    """
    [
        processo_i [
            ficheiro_j [
                { path: str, start: int, end: int } 
            ]
        ]
    ]
    """

    # TODO melhorar o file_idx < len(files)

    # Enquanto o ficheiro não tiver sido totalmente atribuido
    while file_idx < len(files) and file_lines < files[file_idx][1]:
        to_add = min(lines_each, files[file_idx][1] - file_lines)

        file_lines += to_add
        current_lines += to_add

        eof = file_lines >= files[file_idx][1]
        if not eof:
            res[-1][-1]['end'] = files[file_idx][2][file_lines]

        # TODO == ?
        next_process = current_lines >= lines_each
        # Passar ao próximo ficheiro
        if eof:
            file_lines = 0
            file_idx += 1
            if not next_process and file_idx < len(files):
                res[-1].append(
                    { 'path': files[file_idx][0],
                      'start': 0,
                      'end': -1 } )

        # Passar ao próximo processo
        if next_process and file_idx < len(files):
            current_lines = 0
            res.append(
                [
                    {'path': files[file_idx][0],
                     'start': files[file_idx][2][file_lines],
                     'end': -1}
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
    line_offset = []
    offset = 0

    with open(path) as f:
        for line in f:
            line_offset.append(offset)
            offset += len(line)

    return len(line_offset), line_offset

def strip_accents(s: str) -> str:
    """
    Remove acentos de dada string.

    :param s: String a remover os acentos.
    :return: String sem acentos.
    """
    return ''.join(c for c in normalize('NFD', s)
                  if category(c) != 'Mn')

def read_file(file: Dict[str, Union[str, int]]) -> Generator[str, None, None]:
    """
    Lê um ficheiro de dado caminho.

    :param file: Dicionário com o path, o start e end de um ficheiro
    :return: Gerador com a String de uma linha do ficheiro.
    """
    offset = file['start']
    with open(file['path']) as f:
        while True:
            if file['end'] != -1 and offset >= file['end']:
                break

            f.seek(offset, 0)
            line = f.readline()
            if line:
                offset += len(line)
                yield line
            else:
                break

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
    Compila diferentes formatos de palavras, reconhecendo-os como as mesmas palavras.

    :param words: Tuplo de Strings com palavras a compilar.
    :return: Lista de tuplos com pares String palavra e a sua Pattern expressão regular.
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
    """
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
        """
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

def print_results(words: List[str], all_words: bool, count: bool, val: List[str] = None):
    """
    Imprime resultados para o stdout.

    :param words: Lista de Strings com palavra(s).
    :param all_words: Bool cujo True representa se a pesquisa/contagem deve apenas
                      com todas as palavras dadas.
    :param count: Bool cujo True representa se é impressa a quantidade de ocorrências
                  e cujo False a quantidade de linhas.
    :param val: Lista de Strings com valores a escrever.
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

def commit_results(word_occurrences: Dict[str, Dict[int, int]], all_words: bool, count: bool):
    """
    Calcula e regista os resultados globais.

    :param word_occurrences: Dicionário com as ocorrências das palavras em cada linha.
    :param all_words: Bool cujo True representa se a pesquisa/contagem deve apenas
                      com todas as palavras dadas.
    :param count: Bool cujo True representa se é impressa a quantidade de ocorrências
                  e cujo False a quantidade de linhas.
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

def process_files(files: List[Dict[str, Union[str, int]]], words: List[Tuple[str, Pattern]], all_words: bool, count: bool):
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
    print(files)
    for file in files:
        # Pesquisar e contar as palavras
        word_occurrences = search_file(file, words, all_words)
        # Processar e guardar os resultados no Array total
        vals = commit_results(word_occurrences, all_words, count)
        # Imprimir resultados

        mutex.acquire()
        print(f'{Fore.LIGHTMAGENTA_EX}Ficheiro {file["path"]}:{Style.RESET_ALL}')
        print_results(word_occurrences.keys(), all_words, count, vals)
        mutex.release()