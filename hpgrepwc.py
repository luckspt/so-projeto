from pickle import load
from typing import Dict
from datetime import datetime, timedelta
from argparse import ArgumentParser

from colorama import Fore, init
init() # Inicialização colorama

def parse() -> Dict[str, str]:
    """
    Define o parser de argumentos.

    :return: Dict com valores dos argumentos escolhidos pelo utilizador.
    """
    parser = ArgumentParser(description='Lê o histórico de execução do programa pgrepwc')

    parser.add_argument('file',
                        help='Caminho do ficheiro binário.')

    args = parser.parse_args().__dict__

    return args

def unix_to_datetime(unix: int) -> str:
    """
    Transforma uma timestamp unix numa string que representa um datetime
    :param unix: timestamp unix a transformar
    :return: timestamp unix em formato dia/mes/ano hora:minuto:segundo:microsegundo
    """
    return datetime.fromtimestamp(unix / 1000000).strftime('%d/%m/%y %H:%M:%S:%f')

def us_to_time(us: int) -> str:
    """
    Transforma microssegundos numa string que representa um datetime
    :param us: microssegundos a transformar
    :return: os microssegundos em formato hora:minuto:segundo:microsegundo
    """
    return str(timedelta(microseconds=us)).replace('.', ':')

def main() -> None:
    """
    Main
    """
    args = parse()

    with open(args['file'], 'rb') as file:
        dados = load(file)

        inicio = unix_to_datetime(dados['start'])
        duration = us_to_time(dados['duration'])
        opt_all = 'Sim' if dados['all'] else 'Não'

        occurrences = 'ocorrências' if dados['count'] else 'linhas'

        res = [f'Início da execução da pesquisa: {Fore.LIGHTBLACK_EX}.. {Fore.LIGHTGREEN_EX}{inicio}',
               f'{Fore.RESET}Duração da execução: {Fore.LIGHTBLACK_EX}............. {Fore.LIGHTGREEN_EX}{duration}',
               f'{Fore.RESET}Número de processos filhos: {Fore.LIGHTBLACK_EX}...... {Fore.LIGHTGREEN_EX}{dados["children"]}',
               f'{Fore.RESET}Opção -a ativada: {Fore.LIGHTBLACK_EX}................ {Fore.LIGHTGREEN_EX}{opt_all}']

        if dados['interval']:
            res.append(f'{Fore.RESET}Emissão de alarmes no intervalo de {Fore.LIGHTGREEN_EX}{dados["interval"]} segundos')

        for p in dados['processes']:
            res.append(f'{Fore.MAGENTA}Processo: {p["pid"]}')
            for f in p['files']:
                res.append(f'\t{Fore.LIGHTMAGENTA_EX}ficheiro: {f["path"]}')

                duration = us_to_time(f["duration"])
                res.append(f'\t\t{Fore.RESET}tempo de pesquisa: {Fore.LIGHTBLACK_EX}................ {Fore.LIGHTGREEN_EX}{duration}')
                res.append(f'\t\t{Fore.RESET}dimensão do ficheiro: {Fore.LIGHTBLACK_EX}............. {Fore.LIGHTGREEN_EX}{f["lines"]}')

                for i, oc in enumerate(f['occurrences']):
                    res.append(f'\t\t{Fore.RESET}número de {occurrences} da palavra_{i+1}: {Fore.LIGHTGREEN_EX}{oc}')


        print('\n'.join(res))

if __name__ == '__main__':
    try:
        main()
    except UserWarning as w:
        print(w)
