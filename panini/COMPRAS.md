# Ranking de compras

Na pasta `panini`, com Python 3.11 ou superior e as dependências da biblioteca Quadrinhos instaladas, execute:

```powershell
python -m pip install -r requirements-compras.txt
python compras.py ranking-black-friday-2026-11-24.csv --orcamento 100,00 -o recomendacoes.json
```

O orçamento é opcional. A cesta percorre o ranking do maior score para o menor, acrescentando cada edição que cabe no saldo e pulando possíveis duplicatas. Os valores são em reais e excluem frete. Em empates, o menor preço vem primeiro, seguido do título e da URL. O ranking completo continua disponível ao lado da cesta.

Para atualizar os preços, execute o coletor existente e passe o novo CSV ao motor:

```powershell
python panini.py -o ofertas.csv
python compras.py ofertas.csv -o recomendacoes.json
```

Também é possível passar uma URL de categoria ao coletor. Quando ele reporta falhas, grava os resultados disponíveis em um arquivo `.parcial.csv`. Esse arquivo é aceito pelo motor e cobre somente as ofertas coletadas.

## Integração

`--biblioteca CAMINHO` seleciona o projeto Quadrinhos (por padrão, a raiz deste repositório). O motor usa a sessão configurada pela biblioteca, o serviço de listagem da coleção e a função de listagem de desejos. Funciona com o aplicativo fechado. A leitura considera o banco configurado por `DATABASE_URL` ou o SQLite local padrão.

O motor lê os dois formatos CSV encontrados, com cabeçalho, UTF-8 e delimitador ponto e vírgula. Usa os preços em centavos e o desconto em pontos percentuais. A categoria editorial da campanha fica em `linha`. Campos ausentes de editora, formato, estoque e autoria ficam identificáveis no relatório. As datas e a disponibilidade representam a coleta.

## Como interpretar

- `ranking` contém ofertas elegíveis, com preço, link, série, volume, evidências e pontuação. Uma edição desejada que também preenche lacuna recebe as duas contribuições. A classe principal é WISHLIST.
- `match_confidence` mede a correspondência com uma edição específica da estante ou dos desejos, de 0 a 1. A lista `volumes_possuidos` explica separadamente uma continuação ou lacuna. Os números conhecidos de uma série delimitam os buracos internos.
- Correspondências intermediárias e sobreposições de conteúdo seguem para `revisar`, fora da cesta. `descartes` contabiliza edições possuídas, indisponíveis e descobertas abaixo do limiar.
- Cada componente mostra o valor entre 0 e 1, o peso e os pontos somados. O desconto combina a porcentagem e a economia em reais. O preço relativo recebe a contribuição integral até a média paga e diminui acima dela. Dados históricos ausentes aparecem como `null` e contribuem zero. O estoque desconhecido tem contribuição própria.
- O perfil compara frequências de série, personagem, autoria, arco, era e formato com o valor mais frequente de cada campo. A cobertura de personagens e arcos depende dos identificadores disponíveis nos dois sistemas. Uma descoberta precisa atingir o mínimo absoluto configurado, mesmo em coletas com poucos dados.
- Edite `config.toml` para ajustar pesos, limiares, meia-vida, disponibilidade e desconto. Os pesos dos oito componentes somam 100. O motor usa `rapidfuzz.fuzz.ratio` quando instalado. Inclui uma implementação equivalente da distância Indel normalizada para execução offline e informa qual foi usada.

## Histórico opcional

Use `--historico anterior.csv` uma ou mais vezes, com coletas anteriores ao arquivo avaliado. O bônus exige preço igual ou inferior ao menor valor observado para a mesma URL.

Use `--compras compras.json` para fornecer datas de aquisição e preços efetivamente pagos por ID da estante, por exemplo:

```json
{"1": {"data": "2026-06-15", "preco_pago": "24,90"}}
```

`--data 2026-11-24` fixa a referência do decaimento para repetir uma análise. Uma aquisição com idade igual à meia-vida vale metade de uma aquisição atual. Registros sem data recebem peso 1. O ano de publicação não participa desse cálculo. Os preços pagos disponíveis formam a média ponderada.

Execute `python -m unittest -v test_compras` nesta pasta para verificar o motor.
