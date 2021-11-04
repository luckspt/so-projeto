from re import compile, Pattern, findall
from argparse import ArgumentParser
from unicodedata import normalize, category
from typing import List, Dict, Union, Generator, Tuple
from multiprocessing import Value
from colorama import init, Fore, Back, Style
init() #autoreset=True

# Helpers
def read_arr(text: str) -> List[str]:
    files = input(text)
    inp = 'true' # force do-while
    while inp:
        inp = input()
        files += f' {inp}'

    return files.split()

def chunks(lst: List, n: int) -> Generator[List[str], None, None]:
    for i in range(n):
        yield lst[i::n]

def read_file(path: str) -> Generator[str, None, None]:
    with open(path) as f:
        for line in f:
            yield line

def strip_accents(s):
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
    validate_args(args)

    return args

def validate_args(args: Dict[str, Union[str, int, bool, List[str]]]) -> None:
    # Remove duplicates
    args['palavras'] = tuple(set(strip_accents(word).lower() for word in args['palavras']))

    # Enforce limits
    if len(args['palavras']) > 3:
        raise UserWarning('Argument palavras must not be longer than 3.')

    if args['parallelization'] < 0:
        raise UserWarning('Argument -p must not be smaller than 0.')

    # Get files from stdin
    if args['files'] is None:
        args['files'] = read_arr('Insira o(s) ficheiro(s) a pesquisar: ')

    # Remove duplicates
    args['files'] = tuple(set(args['files']))

    # Enforce parallelization limits
    if args['parallelization'] > len(args['files']):
        raise UserWarning(f'Argument -p must not be greater than file count ({len(args["files"])}).')

def compile_words_regex(words: Tuple[str]) -> List[Tuple[str, Pattern]]:
    return [ (word, compile(f'\\b{word}\\b')) for word in words ]

def search_file(path: str, words: List[Tuple[str, List[Pattern]]], all_words: bool) -> Dict:
    occurrences = { word: {} for word, _ in words }
    for i, line in enumerate(read_file(path)):                              #Lê linhas
        normalized_line = strip_accents(line).lower()                            #Tira acentos das palavras

        line_word_occurences = { word: [] for word, _ in words }
        for word, regex in words:                                           #Lê palavras pretendidas
            line_word_occurences[word] = findall(regex, normalized_line)

        # -a Ativo = APENAS 1 p/linha ***OU*** TODAS p/linha
        # -a Não Ativo = APENAS 1 p/linha

        it = (len(line_word_occurences[word]) != 0 for word in line_word_occurences)  # iterator
        # Any consome até ao primeiro True: Not Any verifica se é o único
        is_valid = any(it) and not any(it)

        # Opção -a permite que seja apenas uma ou todas: verificar todas
        if all_words and not is_valid:
            is_valid = all(len(line_word_occurences[word]) != 0 for word in line_word_occurences) #Tem todas as palavras numa linha

        # Processar a quantidade e ocorrências por linha
        if is_valid:
            for word in line_word_occurences:
                qtty = len(line_word_occurences[word])
                if qtty != 0:
                    if i not in occurrences[word]:
                        occurrences[word][i] = 0
                    occurrences[word][i] += qtty

    return occurrences

def print_results(file_path: str, word_occurrences: Dict, all_words: bool, count: bool):
    print(f'{Back.WHITE}{Fore.BLACK}Ficheiro {file_path}:{Style.RESET_ALL}')

    if count:
        for word in word_occurrences:
            occurences = sum(word_occurrences[word][k] for k in word_occurrences[word])
            print(f'A palavra {Fore.CYAN}{word}{Fore.RESET} ocorre {Fore.GREEN}{occurences}{Fore.RESET} vezes.')
    else:
        if all_words:
            # numero de linhas devolvidas da pesquisa
            keys = set(key for word in word_occurrences for key in word_occurrences[word].keys())
            print(f'{Fore.GREEN}{len(keys)}{Fore.RESET} linhas respeitam a pesquisa.')
        else:
            # numero linhas devolvida é por palavra
            for word in word_occurrences:
                print(
                    f'A palavra {Fore.CYAN}{word}{Fore.RESET} ocorre em {Fore.GREEN}{len(word_occurrences[word])}{Fore.RESET} linhas.')

def main():
    args = parse()

    words = compile_words_regex(args['palavras'])

    # Parent does it all when parallelization is 0
    if args['parallelization'] == 0:
        for file_path in args['files']:
            word_occurrences = search_file(file_path, words, args['all'])
            print_results(file_path, words, args['all'], args['count'])
    else:
        print(args['files'])
        children_files = list(chunks(args['files'], args['parallelization']))
        print(children_files)
        for child in children_files:
            # criar criança
            for file_path in child:
                word_occurrences = search_file(file_path, words, args['all'])


if __name__ == '__main__':
    try:
        main()
    except UserWarning as w:
        print(w)
