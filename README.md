# Estante — coleção e aquisições futuras

Execute iniciar.bat e abra http://127.0.0.1:8000. Reinicie o servidor após atualizar os arquivos e pressione Ctrl+F5 no navegador.

## Paginação
A estante exibe 12, 24 ou 48 edições por página. Busca, ordenação e filtros abrangem a coleção completa e voltam à primeira página. Os dados são carregados em lotes de até 500; a paginação visual ocorre no navegador. A lista de desejos exibe 12 itens por página.

## Lista de desejos
Use o menu Lista de desejos e Adicionar desejo. Título obrigatório; ISBN e demais detalhes opcionais. Defina prioridade alta, média ou baixa e anotações. É possível editar ou remover um desejo. Já adquiri transfere a edição para a estante e remove o desejo na mesma transação. ISBNs equivalentes de 10/13 caracteres e títulos iguais são tratados como duplicatas.

## Recomendações de leitura e edições brasileiras
Abra Descobrir e clique em Buscar recomendações. As consultas enviam nomes de títulos, séries e números de volumes à Panini Brasil e, como alternativa, ao Google Books. Não há consulta automática ao abrir a página. Só são exibidas edições confirmadas em páginas de produto da Panini Brasil ou com idioma português e ISBN de grupo brasileiro no Google Books; país de venda sozinho não prova publicação brasileira. O catálogo tem cobertura parcial e pode estar indisponível.

A ordem é: volume faltante entre números já cadastrados, próximo número da mesma série, continuação de história e leituras complementares mapeadas. Só são sugeridos números cuja edição real foi encontrada; não se inventam volumes. Um próximo número que já está nos desejos não causa salto para o seguinte. Numerações com fases/temporadas ambíguas não são tratadas como sequência segura.

A identidade de histórias usa aliases em português/inglês e ignora formatos conhecidos. Ex.: Cavaleiro das Trevas DC de Bolso e edição absoluta são o mesmo conteúdo. Continuações como Contra-Ataca e A Raça Superior têm identidades distintas. Partes numeradas não são confundidas entre si; ter o volume 1 de uma história dividida não equivale a possuir a história completa. Conteúdo do omnibus Batman por Jeph Loeb e Tim Sale também é reconhecido. Obras com sobreposição são omitidas para evitar recompra; isso pode excluir um pacote que contenha também material ainda ausente. Mapeamento por título tem limites: antologias e traduções não cadastradas exigem ampliar os aliases, e números sem informação de fase podem ser ambíguos.

A Saga do Batman, Batman 2025 e cada título Absolute são sequências separadas. Edição absoluta não é o universo Absolute. Ter uma obra não significa que ela foi lida; não existe registro de leitura concluída neste modelo.

Relações iniciais de Batman: Ano Um → O Longo Dia das Bruxas (leitura complementar, não continuação direta); O Longo Dia das Bruxas → Vitória Sombria (continuação); Vitória Sombria → Mulher-Gato: Cidade Eterna (história paralela). As duas últimas têm referências editoriais da DC. Há uma sugestão de Ano Um como base para coleções de Batman que ainda não o contêm. Isso não é uma cronologia obrigatória ou um mapa completo do universo DC. Autor, editora ou personagem em comum isoladamente não bastam para recomendar compra. Séries numeradas genéricas também podem gerar buscas por continuação quando o título explicita volume/parte.

Links: https://www.dc.com/graphic-novels/batman-dark-victory-1999/batman-dark-victory ; https://www.dc.com/comics/catwoman-when-in-rome-2004/catwoman-when-in-rome-1 ; https://panini.com.br/batman-por-jeph-loeb-e-tim-sale-dc-omnibus

Respostas sem falhas ficam em memória por até 15 minutos. Estoque, preço e data de lançamento devem ser conferidos na página da edição. A chave GOOGLE_BOOKS_API_KEY no .env permanece opcional. Execute também python -m unittest test_recomendacoes_leitura -v para validar os casos de conteúdo, idioma, sequência e duplicatas entre formatos.

## Banco e testes
A tabela desejos é criada automaticamente na inicialização; os registros antigos permanecem na tabela quadrinhos. Backups são salvos antes de aplicar atualizações. Execute separadamente python -m unittest test_colecao -v e python -m unittest test_aquisicoes -v. Os testes usam bancos temporários, sem alterar a coleção real.
