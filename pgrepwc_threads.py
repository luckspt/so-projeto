from re import compile, Pattern, findall
from argparse import ArgumentParser
from unicodedata import normalize, category
from typing import List, Dict, Union, Generator, Tuple
from threading import Thread, Lock
from colorama import init, Fore, Back, Style
init() #autoreset=True

mutex = Lock()
total = [0, 0, 0]

# Helpers
def read_list(text: str) -> List[str]:
    inp = input(text)
    files = inp

    # Enquanto a linha não for vazia lê mais valores
    while inp:
        inp = input()
        files += f' {inp}'

    # Partir os valores pelo espaço
    return files.split()

def chunks(lst: List, n: int) -> Generator[List[str], None, None]:
    for i in range(n):
        yield lst[i::n]

def read_file(path: str) -> Generator[str, None, None]:
    with open(path) as f:
        for line in f:
            yield line

def strip_accents(s: str) -> str:
   return ''.join(c for c in normalize('NFD', s)
                  if category(c) != 'Mn')

# Parsing
def parse() -> Dict[str, Union[str, int, bool, Tuple[str]]]:
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
    # Remover duplicados
    args['palavras'] = tuple(set(strip_accents(word).lower() for word in args['palavras']))

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
    # usar o compile da biblioteca re para melhor desempenho, ao invés de definir o regex das palavras em cada linha de cada ficheiro
    return [ (word, compile(f'\\b{word}\\b')) for word in words ]

def search_file(path: str, words: List[Tuple[str, List[Pattern]]], all_words: bool) -> Dict[str, Dict[int, int]]:
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

def commit_results(word_occurrences: Dict, all_words: bool, count: bool):
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
    args = parse()

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
            processos.append( Thread(target=process_files, args=(child_files, words, args['all'], args['count'])) )

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
    except UserWarning as w:
        print(w)

#Palavras "aa", "bb", "cc"
#Com o -a:
#   aa bb CC DD EE  #Conta porque tem todas
#   aa bb DD EE FF  #Não conta porque tem apenas 2
#   aa DD EE FF GG  #Conta porque só tem 1
#Sem o -a:
#   aa bb cc dd ee  #Não conta porque tem todas
#   aa bb dd ee ff  #Não conta porque tem apenas 2
#   aa dd ee ff gg  #Conta porque só tem 1

#Com o -l:
#(Com -a ativo)
#Nº total de linhas encontrada
#   Total: X
#(Com -a não ativo)
#Nº total de linhas encontradas p/palavra
#   aa: X
#   bb: Y
#   cc: Z



# pesquisa até um máximo de três palavras em um ou mais ficheiros, devolvendo as linhas de
# texto que contêm unicamente uma das palavras (isoladamente) ou todas as palavras. Também,
# conta o número de ocorrências encontradas de cada palavra e o número de linhas devolvidas de
# cada palavra ou de todas as palavras

# Dar return a:
# - Quantas linhas contêm unicamente uma das palavras ou todas as palavras
# - Nº de ocorrências por palavra
# - Nº de linhas por palavra ou todas as palavras
#
# Quando -a está ativo:             |  Quando -a não está ativo :
# - Total linhas só com 1 palavra   |  - Totla das linas só com 1 palavra e com todas
#                                       V V V V V V V V V V V V
# Quando -l está ativo com o -a     |  Quando -l está ativo sem o -a
# - Total de linhas                 |  - Total de linhas por palavra
#
# Quando -c está ativo: