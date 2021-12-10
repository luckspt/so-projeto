from argparse import ArgumentParser
from multiprocessing import Array, Lock, Process
from re import compile, findall
from typing import Dict, Generator, List, Pattern, Tuple, Union
from unicodedata import category, normalize
from subprocess import check_output
from colorama import Fore, Style, init
import signal, sys, time

init() # Inicialização colorama

mutex = Lock()
total = Array("i", 3) # Inicialização do contador global das palavras (máx. 3 palavras)

### Helpers
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

def chunks(files: List[str], n: int):
    """
    Gera dado número de combinações de elementos de uma lista.

    :param files: Lista de caminhos de ficheiros.
    :param n: TODO escrever isto.
    :return: Gerador com a Lista de Strings com combinações
             de elementos de dada lista.
    """
    chars_files = [wc(file_path) for file_path in files]
    chars_total = sum(chars_files)
    chars_process = chars_total // n # TODO arredondar acima ou abaixo?

    """
    a prof diz que se pode ler o ficheiro no pai para saber a qtd linhas (e saber a posição de cada para o seek)
        vale a pena ser justo no comprimento da linha ou basta na qtd linhas?
        pode-se usar isso e passar como argumento para o filho, para ele saber que ficheiros tem de processar e em que posição
    
        qdo se lê o ficheiro fazer um seek() para ter a certeza que se está na linha certa mesmo havendo vários processos no mesmo ficheiro
    """
    print('asd')


# TRAB2
# fazer o offset, yield das proximas linhas
# read_line() para consumir a linha só se não for 0
# confirmar que não é preciso mais seeks

def read_file(path: str, file_offset: int) -> Generator[str, None, None]:
    """
    Lê um ficheiro de dado caminho.

    :param path: String com o caminho do ficheiro a ler.
    :return: Gerador com a String de uma linha do ficheiro.
    """
    with open(path) as f:
        # while True:
        #     f.seek(file_offset, 0)
        #     line = f.readline()
        #     if line:
        #         file_offset += len(line)
        #             yield line
        #     else:
        #         break
        pass

def wc(path: str):
    return int(check_output(['wc', '-c', path]).split()[0])

chars = wc('data/file0.txt')
file_offset = chars / 2

def strip_accents(s: str) -> str:
    """
    Remove acentos de dada string.

    :param s: String a remover os acentos.
    :return: String sem acentos.
    """
    return ''.join(c for c in normalize('NFD', s)
                  if category(c) != 'Mn')

### Parsing
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

def search_file(path: str, words: List[Tuple[str, List[Pattern]]], all_words: bool) -> Dict[str, Dict[int, int]]:
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
    '''
        Chave: palavra
        Valor: Dict
                Chave: índice da linha
                Valor: Quantidade de ocorrências [da palavra] nessa linha
    '''

    # For each line of file
    for i, line in enumerate(read_file(path)):
        # Remove diacritics
        normalized_line = strip_accents(line)

        # Dicionário das ocorrências das palavras na linha i
        line_word_occurrences = { word: 0 for word, _ in words }
        '''
            Chave: palavra
            Valor: Quantidade de ocorrências [da palavra] na linha i
        '''

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

def process_files(files: List[str], words: List[Tuple[str, Pattern]], all_words: bool, count: bool):
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
    for file_path in files:
        # Pesquisar e contar as palavras
        word_occurrences = search_file(file_path, words, all_words)
        # Processar e guardar os resultados no Array total
        vals = commit_results(word_occurrences, all_words, count)
        # Imprimir resultados

        mutex.acquire()
        print(f'{Fore.LIGHTMAGENTA_EX}Ficheiro {file_path}:{Style.RESET_ALL}')
        print_results(word_occurrences.keys(), all_words, count, vals)
        mutex.release()

def main():
    """
    Processa e divide a pesquisa/contagem de ficheiros por processos (se aplicável).
    """
    # args = parse()
    args = {
        'palavras': ['batatas', 'milho', 'antonio'],
        'all': False,
        'count': True,
        'files': ['data/file0.txt'],
        'parallelization': 3
    }

    words = compile_words_regex(args['palavras'])
    for i in range(len(words)):
        total[i] = 0

    # O pai faz a pesquisa e contagem quando parallelization é 0
    if args['parallelization'] == 0:
        process_files(args['files'], words, args['all'], args['count'])
    else:
        # dividir a lista de ficheiros em args['parallelization'] sub-listas
        children_files = list(chunks(args['files'], args['parallelization']))

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

    signal.signal(signal.SIGINT, interrupcao)


def interrupcao(sig, NULL):
    global parar
    parar = True


if __name__ == '__main__':
    try:
        main()
        pass
    except UserWarning as w:
        print(w)