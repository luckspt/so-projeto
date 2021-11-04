from re import compile, Pattern,
from argparse import ArgumentParser
from unicodedata import normalize, category
from typing import List, Dict, Union, Generator, Tuple
from re import findall
from multiprocessing import Value

from colorama import init, Fore, Back, Style
init() #autoreset=True

'''
l: List[int] = [1, 2, 3]
t1: Tuple[float, str, int] = (1.0, 'two', 3)
t2: Tuple[int, ...] = (1, 2.0, 'three')
d: Dict[str, int] = {'uno': 1, 'dos': 2, 'tres': 3}
'''

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

    parser.add_argument('-p', '--parallelization', type=int, default=1,
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
    args['palavras'] = set(args['palavras'])

    # Normalize words
    args['palavras'] = tuple(strip_accents(word) for word in args['palavras'])

    # Enforce limits
    if len(args['palavras']) > 3:
        raise UserWarning('Argument palavras must not be longer than 3.')

    if args['parallelization'] < 1:
        raise UserWarning('Argument -p must not be smaller than 1.')

    # Get files from stdin
    if args['files'] is None:
        args['files'] = read_arr('Insira o(s) ficheiro(s) a pesquisar: ')

    # Remove duplicates
    args['files'] = tuple(set(args['files']))

    # Enforce parallelization limits
    if args['parallelization'] > len(args['files']):
        args['parallelization'] = len(args['files'])

def compile_words_regex(words: List[str]) -> List[Pattern]:
    return [ compile(f'\\b{word}\\b') for word in words ]

def search_file(path: str, words: Tuple[str, List[Pattern]], all_words: bool):
    contaLinhas = 0
    occurrences = { word: [] for word in words[0] }
    for i, line in enumerate(read_file(path)):                  #Lê linhas
        normalized = strip_accents(line)                        #Tira acentos das palavras

        line_word_occurences = { word: [] for word in words[0] }
        for word, regex in words:                                      #Lê palavras pretendidas
            line_word_occurences = findall(regex, line)

            if all_words:                                       # ver se todas as palavras tem len != 0
                conta
            else:                                              #if len()=1 invés do ELSE
                pass                                           # ver se ha mais de uma palavra com len != 0

            if word in normalized:         #Verifica se palavras pretendidas estão nas linhas
                occurrences[word].append(i)


def main():
    args = parse()

    # Parent does it all when parallelization is 1
    if args['parallelization'] == 1:
        # parent
        pass
    else:
        children_files = chunks(args['files'], args['parallelization'])
        words = (args['palavras'], compile_words_regex(args['palavras']))

        for file_path in children_files:
            search_file(file_path, words, args['all'])

if __name__ == '__main__':
    try:
        main()
    except UserWarning as w:
        print(w)

