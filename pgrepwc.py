from argparse import ArgumentParser
from unicodedata import normalize
from typing import List

'''
l: List[int] = [1, 2, 3]
t1: Tuple[float, str, int] = (1.0, 'two', 3)
t2: Tuple[int, ...] = (1, 2.0, 'three')
d: Dict[str, int] = {'uno': 1, 'dos': 2, 'tres': 3}
'''

if __name__ == '__main__':
    parser = ArgumentParser(usage='pgrepwc [-a] [-c|-l] [-p n] {palavras} [-f \ficheiros]',
                            description='Pesquisa até três palavras em pelo menos um ficheiro, \
                                         devolvendo as linhas que contêm unicamente uma das ou \
                                         todas as palavras. Conta e pesquisa paralelamente os \
                                         números de ocorrências de cada palavra e de linhas \
                                         devolvidas de cada/todas as palavra(s), devolvendo-os.')


    parser.add_argument(
        '-a', '--all', action='store_true', help='Opção que define se o comando pesquisa as \
                                                  linhas de texto que contêm unicamente uma das \
                                                  palavras ou todas as palavras. Por omissão, \
                                                  pesquisa as linhas contendo unicamente uma \
                                                  das palavras.')
    parser.add_argument(
        '-c', '--count', action='store_true', help='Opção que obtém o número de ocorrências \
                                                    das palavras a pesquisar.')
    parser.add_argument(
        '-l', '--lines', action='store_true', help='Opção que permite obter o número de \
                                                    linhas devolvidas. Caso a opção -a não \
                                                    esteja ativa, o número de linhas \
                                                    devolvido é por palavra.')
    parser.add_argument(
        '-p', '--parallelization', type=int, default=1, help='Opção que permite definir o nível de \
                                                              paralelização n do comando. Por \
                                                              omissão, não há paralelização.')
    parser.add_argument(
            'palavras', nargs='+', help='As palavras a pesquisar no conteúdo dos ficheiros. \
                                         Máximo 3 palavras.')
    parser.add_argument(
        '-f', '--files', nargs='+', help='Ficheiro(s), sobre o(s) qual(is) é efetuada a pesquisa e \
                                          contagem. Por omissão, o comando pede o(s) ficheiro(s) \
                                          ao utilizador.')

    args = parser.parse_args()

    try:
        if len(args.palavras) > 3:
            parser.error('Argument palavras must not be longer than 3.')

        # -c e -l são mutuamente exclusivos
        if args.count and args.lines:
            parser.error('Arguments -c and -l are mutually exclusive.')

        # estar antes de pedir os ficheiros permite uma melhor utilização
        if args.parallelization < 1:
            parser.error('Argument -p must not be smaller than 1.')

        # Obter a lista de ficheiros do stdin
        if args.files is None:
            args.files = read_files()

        # Remover duplicados
        args.files = list(set(args.files))

        # Paralelização não superior a qtd ficheiros
        if args.parallelization > len(args.files):
            args.parallelization = len(args.files)

        print(args.__dict__)
    except UserWarning as w:
        print(w)

# remove diacritics normalize('NFD', 'josé')

def read_files() -> List[str]:
    files = input('Insira a localização dos ficheiros: ')
    inp = 'dummy'
    while inp:
        inp = input()
        files += f' {inp}'

    return files.split()