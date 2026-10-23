# Estante — coleção e aquisições futuras

Execute iniciar.bat e abra http://127.0.0.1:8000. Reinicie o servidor após atualizar os arquivos e pressione Ctrl+F5 no navegador.

## Paginação
A estante exibe 12, 24 ou 48 edições por página. Busca, ordenação e filtros abrangem a coleção completa e voltam à primeira página. Os dados são carregados em lotes de até 500; a paginação visual ocorre no navegador. A lista de desejos exibe 12 itens por página.

## Lista de desejos
Use o menu Lista de desejos e Adicionar desejo. Título obrigatório; ISBN e demais detalhes opcionais. Defina prioridade alta, média ou baixa e anotações. É possível editar ou remover um desejo. Já adquiri transfere a edição para a estante e remove o desejo na mesma transação. ISBNs equivalentes de 10/13 caracteres e títulos iguais são tratados como duplicatas.

## Recomendações
Abra Para sua próxima aquisição e clique em Buscar recomendações. A consulta envia nomes de coleções e autores ao Google Books. Não ocorre automaticamente ao abrir a página. Até quatro buscas usam as coleções e autores mais frequentes; as respostas são guardadas em memória por até 15 minutos quando não há falhas.

O algoritmo pontua coleção em comum (60 mais frequência limitada a 5), autor em comum (25), personagem/universo reconhecido no título (15) e editora (5). Exige pelo menos 15 pontos e evidência de quadrinhos/mangás, universo reconhecido ou mesma série. Exclui edições já cadastradas ou desejadas por ISBN equivalente e título normalizado. Mostra até 24 sugestões com motivos e link da fonte. Não é um catálogo exaustivo de volumes faltantes; títulos e metadados incompletos podem afetar a classificação. A fonte pode retornar títulos em outros idiomas. Estoque e preço não são consultados.

O Google Books pode aplicar cotas ou ficar indisponível. Uma chave própria em GOOGLE_BOOKS_API_KEY no arquivo .env é opcional e usada quando presente; não garante resultados ou disponibilidade. Se o catálogo falhar, a interface exibe um aviso, sem inventar títulos. Testes usam respostas simuladas para serem repetíveis.

## Banco e testes
A tabela desejos é criada automaticamente na inicialização; os registros antigos permanecem na tabela quadrinhos. Backups são salvos antes de aplicar atualizações. Execute separadamente python -m unittest test_colecao -v e python -m unittest test_aquisicoes -v. Os testes usam bancos temporários, sem alterar a coleção real.
