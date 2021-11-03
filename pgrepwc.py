from argparse import ArgumentParser
from unicodedata import normalize
from typing import List
from multiprocessing import Value
from math import ceil

'''
l: List[int] = [1, 2, 3]
t1: Tuple[float, str, int] = (1.0, 'two', 3)
t2: Tuple[int, ...] = (1, 2.0, 'three')
d: Dict[str, int] = {'uno': 1, 'dos': 2, 'tres': 3}
'''

# remove diacritics normalize('NFD', 'josé')

def read_files() -> List[str]:
    files = input('Insira a localização dos ficheiros: ')

    input = True

    while input:
        input = input()
        files += f' {input}'

    return files.split() ##["t1.txt", "t2.txt"]

def daddy(files, nr_children = None):
    #Se houver paralelização
    if nr_children:
        #Arredonda a divisão inteira para excesso
        max_files_per_child = ceil(len(files) / nr_children)

        #Para cada filho pedido no comando
        for child in range(nr_children):
            #Inicializamos os ficheiros que lhe ficam atribuídos a 0
            child_files = []

            #Enquanto houverem ficheiros por distribuir
            while len(files) > 0:
                #Até atingirmos o máximo de ficheiros que podemos atribuir a este filho
                for nr in range(max_files_per_child):
                    #Retiramos um ficheiro dos ficheiros por distribuir e associamo-lo ao filho
                    child_files.append(files.pop(0))

if __name__ == '__main__':
    parser = ArgumentParser(usage='pgrepwc [-a] [-c|-l] [-p n] {palavras} [-f \ficheiros]',
                            description='Pesquisa até três palavras em pelo menos um ficheiro, \
                                         devolvendo as linhas que contêm unicamente uma das ou \
                                         todas as palavras. Conta e pesquisa paralelamente os \
                                         números de ocorrências de cada palavra e de linhas \
                                         devolvidas de cada/todas as palavra(s), devolvendo-os.')

    mutually_exclusive = parser.add_mutually_exclusive_group(required=True)

    parser.add_argument(
        '-a', '--all', action='store_true', help='Opção que define se o comando pesquisa as \
                                                  linhas de texto que contêm unicamente uma das \
                                                  palavras ou todas as palavras. Por omissão, \
                                                  pesquisa as linhas contendo unicamente uma \
                                                  das palavras.')
    mutually_exclusive.add_argument(
        '-c', '--count', action='store_true', help='Opção que obtém o número de ocorrências \
                                                    das palavras a pesquisar.')
    mutually_exclusive.add_argument(
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

        if args.count and args.lines:
            parser.error('Arguments -c and -l are mutually exclusive.')

        #Testar antes de pedir os ficheiros permite uma melhor utilização
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
