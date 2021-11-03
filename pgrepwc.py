from argparse import ArgumentParser
from unicodedata import normalize
from typing import List

'''
l: List[int] = [1, 2, 3]
t1: Tuple[float, str, int] = (1.0, 'two', 3)
t2: Tuple[int, ...] = (1, 2.0, 'three')
d: Dict[str, int] = {'uno': 1, 'dos': 2, 'tres': 3}
'''

# remove diacritics normalize('NFD', 'josé')

def read_files() -> List[str]:
    files = input('Insira a localização dos ficheiros: ')
    inp = 'dummy'
    while inp:
        inp = input()
        files += f' {inp}'

    return files.split()


###################################################################################################

if __name__ == '__main__':
    parser = ArgumentParser(usage='pgrepwc [-a] [-c|-l] [-p n] {palavras} [-f ficheiros]', description='Pesquisa até um máximo de três palavras em um ou mais ficheiros, devolvendo as linhas de texto que contêm unicamente uma das palavras (isoladamente) ou todas as palavras. Também, conta o número de ocorrências encontradas de cada palavra e o número de linhas devolvidas de cada palavra ou de todas as palavras. A pesquisa e contagem são realizadas em paralelo, em vários ficheiros')
    parser.add_argument('palavras', nargs='+', help='as palavras a pesquisar no conteúdo dos ficheiros. O número máximo de palavras a pesquisar é de 3. ')
    parser.add_argument(
        '-a', '--all', action='store_true', help='opção que define se o resultado da pesquisa são as linhas de texto que contêm unicamente uma das palavras ou todas as palavras. Por omissão (ou seja, se a opção não for usada), somente as linhas contendo unicamente uma das palavras serão devolvidas.')
    parser.add_argument(
        '-c', '--count', action='store_true', help='opção que permite obter o número de ocorrências encontradas das palavras a pesquisar.')
    parser.add_argument(
        '-l', '--lines', action='store_true', help='opção que permite obter o número de linhas devolvidas da pesquisa. Caso a opção -a não esteja ativa, o número de linhas devolvido é por palavra.')
    parser.add_argument(
        '-p', '--parallelization', type=int, default=1, help='opção que permite definir o nível de paralelização n do comando (ou seja, o número de processos (filhos)/threads que são utilizados para efetuar as pesquisas e contagens). Por omissão, deve ser utilizado apenas um processo (o processo pai) para realizar as pesquisas e contagens.')
    parser.add_argument(
        '-f', '--files', nargs='+', help='podem ser dados um ou mais ficheiros, sobre os quais é efetuada a pesquisa e contagem. Caso não sejam dados ficheiros na linha de comandos (ou seja, caso não seja passada a opção -f), estes devem ser lidos de stdin (o comando no início da sua execução pedirá ao utilizador quem são os ficheiros a processar).')

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
            args.parallelization = args.files

        print(args.__dict__)
    except UserWarning as w:
        print(w)


###################################################################################################


obj = {
    'username': 'ok',
    'content': '<@733730624350847029>',
    'icon_url': 'https://cdn.discordapp.com/emojis/756547331025010709.gif',
    'embeds': [ {
        'title': 'sexo',
        'description': 'الجنس ملحمة الجنس جدا أحب الجنس نعم!!!!!!!\nNAS CRIANÇAS NÃO TOCA NAS CRIANÇAAAAS! (assasino,bandido! Assassino, bandido! És um bandido! És um bandido pedófilo!) Não toca na criança\ ($',
        'image': {
            'url': 'https://c.tenor.com/8_e3rKfcpywAAAAC/zeri-hub-kawakie.gif'
        },
        'thumbnail': {
            'url': 'https://c.tenor.com/TofJrkqD9JMAAAAd/impressed-awsome.gif'
        },
        'author': {
            'name': 'ruca preto',
            'url': 'https://cdn.discordapp.com/emojis/756547331025010709.gif',
            'icon_url': 'https://cdn.discordapp.com/emojis/756547331025010709.gif'
        }
    }
        ]
    }