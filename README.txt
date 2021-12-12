Grupo 19 - 12/12/2021

53741 - Lívia Batalha
56926 - Lucas Pinto
56941 - Bruno Gonzalez

PGREPWC
Utilização:
• pgrepwc [-a] [-c|-l] [-p n] [-w s] [-o file] {palavras} [-f ficheiros]

Funcionalidades:
• Suporta paralelismo de processos.
• Garantia de isenção de repetições da pesquisa/contagem de palavras com o método chunks.
• Garantia de isenção de repetições de ficheiros a pesquisar com o método validate_args.
• Recorrência ao Lock() para sincronização de processos sem problemas e escrita de resultados no STDOUT não intercalada.
• Recorrência de mecanismos de memória partilhada com Array do módulo multiprocessing para passar resultados ao processo pai.
• Recorrência a expressões regulares para pesquisa/contagem de todas as ocorrências das palavras pretendidas com o módulo re.
• Resultados dos programas no STDOUT realçados a cores para melhor visualização graças à utilização do pacote Colorama.
• Leitura de caminhos/nomes de ficheiros através do comando inicial ou como argumento.
• Código documentado e comentado para melhor legibilidade.
• Pesquisa de palavras é case-sensitive;
• Divisão equitativa do conteúdo de ficheiros pelos processos filho;
• Término do processamento de ficheiros quando o processo pai recebe o sinal SIGINT (i.e., CTRL+C);
• Possibilidade de definição do intervalo de tempo em que o processo pai escreve para stdout o estado da contagem até ao momento;
• Possibilidade de definição do ficheiro de saída;
• Armazenamento da informação sobre a pesquisa, contagem e processo(s) em binário num ficheiro de saída.

Limitações:
• O caminho/nome dos ficheiros não pode ter espaços (e.g. "ficheiro_com espaço.txt" não é alcançável pelo pgrepwc.py.
• Não lê ficheiros binários.

Observações:
• Tomámos a liberdade de dividir sempre o conteúdo dos ficheiros pelos processos, em vez de apenas quando o nível de paralelização é maior que o número de ficheiros. Consideramos que é uma abordagem mais justa e eficiente, e, portanto, justificada.



HPGREPWC
• hpgrepwc file

Funcionalidades:
• Lê o histórico de execução de um ficheiro binário criado pelo programa pgrepwc.py;
• Converte binário para texto e apresenta a informação no stdout.

Limitações:
• O caminho/nome do ficheiro não pode ter espaços (e.g. "ficheiro_com espaço.txt" não é alcançável pelo hpgrepwc.py.
