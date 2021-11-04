import math
from typing import List, Tuple

files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i']
children = 7

def chunkify(lst: List, n: int) -> Tuple[List[str]]:
    return ( lst[i::n] for i in range(n) )

children_files = list(chunkify(files, children))
print(children_files)

# children_files = []
# for child in range(children):
#     # Inicializamos os ficheiros que lhe ficam atribuídos a 0
#     # Os primeiros (todos se o resto da divisão de ficheiros for 0) filhos recebem o número máximo de ficheiros
#     if len(files) >= files_per_child:
#         children_files.append(slice(files[files_per_child]))
#         del files[:files_per_child]
#
#     # Se o resto da divisão de ficheiros for != 0, o último filho fica com os restantes ficheiros por atribuir
#     else:
#         children_files.append(files)
# print(children_files)