from pickle import dump
from argparse import ArgumentParser
from unicodedata import normalize, category
from re import findall
from typing import List, Dict, Union, Generator, Tuple, Pattern
from multiprocessing import Array, Process, Lock, Value
from colorama import init, Fore, Style
from datetime import date
from time import time

import signal

init() # Inicialização colorama

mutex   = Lock()
total   = Array("i", 3) # Inicialização do contador global das palavras (máx. 3 palavras)
parar   = False
nFilhos = Value("i", 0)
diaInicial  = date.today().strftime("%d/%m/%Y")
horaInicial = date.today().strftime("%H:%M:%S:%f")
temposProcessos = [0,0,0]

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

def chunks(lst: List, n: int) -> Generator[List[str], None, None]:
    """
    Gera dado número de combinações de elementos de uma lista.
    :param lst: Lista a subdividir em combinações.
    :param n: Int número máximo de elementos por combinação.
    :return: Gerador com a Lista de Strings com combinações
             de elementos de dada lista.
    """
    for i in range(n):
        yield lst[i::n]

def read_file(path: str) -> Generator[str, None, None]:
    """
    Lê um ficheiro de dado caminho.
    :param path: String com o caminho do ficheiro a ler.
    :return: Gerador com a String de uma linha do ficheiro.
    """
    with open(path) as f:
        for line in f:
            yield line

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
                        help='Define se o comando pesquisa as linhas de texto que contêm \
                            unicamente uma das palavras ou todas as palavras. Por omissão, pesquisa \
                            as linhas contendo unicamente uma das palavras.')

    mutually_exclusive.add_argument('-c', '--count', action='store_true',
                                    help='Obtém o número de ocorrências das palavras a pesquisar.')

    mutually_exclusive.add_argument('-l', '--lines', action='store_true',
                                    help='Obtém o número de linhas devolvidas. \
                                        Caso a opção -a não esteja ativa, o número de linhas \
                                        devolvido é por palavra.')

    parser.add_argument('-p', '--parallelization', type=int, default=0,
                        help='Define o nível de paralelização n do comando. \
                            Por omissão, não há paralelização.')

    parser.add_argument('-w', '--interval', type=int, default=0,
                        help='Define o intervalo de tempo s em que o estado da contagem de \
                         linhas ou ocorrências é escrito.')

    parser.add_argument('-o', '--output', type=str,
                        help='Define o ficheiro file que guarda o histórico da execução do programa em binário.')

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
        # Remove diacritics and make lowercase for case-insensitive comparison
        normalized_line = strip_accents(line).lower()

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
        inicioProcesso = date.today().strftime("%H:%M:%S")

        nFilhos.value = nFilhos + 1

        # Pesquisar e contar as palavras
        word_occurrences = search_file(file_path, words, all_words)
        # Processar e guardar os resultados no Array total
        vals = commit_results(word_occurrences, all_words, count)
        # Imprimir resultados

        mutex.acquire()
        print(f'{Fore.LIGHTMAGENTA_EX}Ficheiro {file_path}:{Style.RESET_ALL}')
        print_results(word_occurrences.keys(), all_words, count, vals)
        mutex.release()

        fimProcesso = date.today().strftime("%H:%M:%S")

        temposProcessos[nFilhos.value-1] = fimProcesso-inicioProcesso

        if parar:
            exit()

def main():
    """
    Processa e divide a pesquisa/contagem de ficheiros por processos (se aplicável).
    """
    args = parse()
    signal.signal(signal.SIGINT, interrupcao)

    if args['output'] or args['w']:
        tempo_comeca = time()

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
        print(f'{Fore.LIGHTRED_EX}Total{" até ao momento" if parar else ""}:{Style.RESET_ALL}')
        # A partir do Python 3.7 os dicionários são ordenados, portanto pode-se usar a lista inicial das palavras
        print_results(args['palavras'], args['all'], args['count'])

    if args['w'] or args['output']:
        print((time()-tempo_comeca)*1000000, "micro-segundos.")

    if args['output']:
        output(args, int(tempo_comeca*1000), int(tempo_comeca-time() * 1000))


def interrupcao(sig, NULL):
    parar = True

###################### OPÇÃO -O ########################

def output(args: Dict[str, Union[str, int, bool, Tuple[str]]], inicio: int, duracao: int):
    # if args['all'] != None

    porEscrever = {
        'diainicio': diaInicial,
        'horainicio': horaInicial,
        'duracao': horaInicial - date.today().strftime("%H:%M:%S:%f"),
        'processos_filhos': args['parallelization'],
        'opcao_a': args['all'] != None,
        'alarmes_intervalo': args['interval'],
        'processos': []
    }

    for i in range(args['parallelization']):
        porEscrever['processos'].append([])
        # for ficheiro in ficheirosFilho[i]:
        porEscrever['processo'].append({'path': 'asd.txt', 'tempo': temposProcessos[i], 'dimensao': 123, 'ocorrencias': [ 3, 4, 5 ]})

    # n -> Nº Filhos de -p  s -> Intervalo de -w
    # Observações:
    # (1) caso a opção -p e -w não sejam ativadas, o valor n e s serão zero;
    # (2) a vermelho significa que a linha do histórico sobre a contagem é
    # definida de acordo com o tipo da contagem, ou seja, aparecerá “número
    # de ocorrências” ou “número de linhas”. O número destas linhas terá de
    # aparecer de acordo com o número de palavras a pesquisar.

    with open('file2.bin', 'wb') as file:
        dump(porEscrever, file)

########################################################


if __name__ == '__main__':
    try:
        # main()
        output()
    except UserWarning as w:
        print(w)
