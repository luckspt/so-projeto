Grupo 19 - 07/11/2021

53741 - Lívia Batalha
56926 - Lucas Pinto
56941 - Bruno Gonzalez

Comandos a executar:
• python3 grepwc.py [-a] [-c|-l] [-p n] {palavras} [-f ficheiros]
• python3 grepwc_threads.py [-a] [-c|-l] [-p n] {palavras} [-f ficheiros]

Funcionalidades:
• Suporta paralelismo de processos (pgrepwc.py) e de threads (pgrepwc_threads.py).
• Garantia de isenção de repetições da pesquisa/contagem de palavras com o método chunks.
• Garantia de isenção de repetições de ficheiros a pesquisar com o método validate_args.
• Recorrência ao Lock() para sincronização de processos/threads sem problemas e escrita de resultados no STDOUT não intercalada.
• Recorrência de mecanismos de memória partilhada com Array do módulo multiprocessing para passar resultados ao processo pai (pgrepwc.py).
• Recorrência a expressões regulares para pesquisa/contagem de todas as ocorrências das palavras pretendidas com o módulo re.
• Resultados dos programas no STDOUT realçados a cores para melhor visualização graças à utilização do pacote Colorama.
• Leitura de caminhos/nomes de ficheiros através do comando inicial ou como argumento.
• Código documentado e comentado para melhor legibilidade.

Limitações:
• O caminho/nome dos ficheiros não pode ter espaços (e.g. "ficheiro_com espaço.txt" não é alcançável no pgrepwc.py/pgrepwc_threads.py).

Observações:
• Se o comando não incluir a opção -a, a contagem só tem em conta as ocorrências/linhas em que a(s) palavra(s) ocorrem isoladamente.
  Se o comando incluir a opção -a, a contagem só tem em conta as ocorrências/linhas em que a(s) palavra(s) ocorrem isoladamente e em que ocorrem todas.

  Em nenhuma altura, a contagem de ocorrências/linhas considera linhas em que algumas palavras ocorrem, ou seja, nem apenas uma, nem apenas todas.

  E.G. Dadas as palavras "aa", "bb" e "cc" e as linhas L1: "aa bb CC DD EE", L2:"aa bb DD EE FF" e L3:"aa DD EE FF GG":
       O pgrepwc nunca considera para qualquer contagem ou qualquer opção a linha L2, porque esta contém mais que uma das palavras, mas não todas.