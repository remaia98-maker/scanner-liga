# Scanner Liga

App web pessoal para ler cartas de Pokémon TCG e One Piece Card Game pela câmera do celular e gerar um CSV no formato de importação de coleção da LigaPokemon ou da LigaOnePiece. O seletor no topo da tela inicial escolhe o jogo; cada jogo tem o próprio lote.

## Arquivos

| Arquivo | Para que serve |
| --- | --- |
| `index.html` | O app (tela, câmera, lote e exportação) |
| `core.js` | Pokémon: leitura do texto, busca no catálogo e geração do CSV |
| `core-op.js` | One Piece: leitura do código, versões da carta, busca, imagens e CSV da LigaOnePiece |
| `catalog.json` | Catálogo de Pokémon (TCGdex, TCGplayer e os nomes da Liga nas coleções dos seus exports) |
| `catalog-op.json` | Catálogo de One Piece: edições e cartas dos exports da LigaOnePiece (pasta `liga-op/`), completado com a base oficial da Bandai |
| `manifest.webmanifest`, `icon-*.png` | Ícone e nome ao adicionar à Tela de Início |

## Publicar no GitHub Pages (grátis)

1. Crie uma conta em github.com, se ainda não tiver.
2. Clique em **New repository**. Nome: `scanner-liga`. Deixe **Public** e clique em **Create repository**.
3. Na página do repositório, clique em **uploading an existing file** (ou **Add file → Upload files**).
4. Arraste todos os arquivos desta pasta (não a pasta em si) e clique em **Commit changes**.
5. Vá em **Settings → Pages**. Em **Branch**, escolha `main` e a pasta `/ (root)`, e clique em **Save**.
6. Espere 1 ou 2 minutos. O endereço aparece no topo dessa mesma página, no formato `https://SEU-USUARIO.github.io/scanner-liga/`.

## Instalar no iPhone

1. Abra o endereço no **Safari**.
2. Toque em **Compartilhar → Adicionar à Tela de Início**.
3. Abra pelo ícone. Na primeira vez que tocar em **Abrir câmera**, permita o acesso.

Na primeira leitura, o app baixa o leitor de texto (Tesseract, cerca de 10 MB). Depois disso, ele fica guardado no aparelho.

## Como usar

- **Início:** o app abre na busca (nome, número ou sigla, com filtros para japonesas, promos e antigas). Abaixo aparecem as últimas cartas adicionadas e um resumo do lote.
- **Câmera contínua:** o botão redondo âmbar abre a câmera. O app lê só a faixa de baixo da carta (sigla e número): aproxime até essa faixa ocupar o retângulo, mesmo que o resto da carta saia da tela. No Android, use o zoom (1,5× ou 2×) para não precisar chegar tão perto. Cada carta reconhecida entra no lote sozinha; a mesma carta só conta de novo depois de sair e voltar para o retângulo. Use **Pausar**, **Editar** e **Desfazer** no painel de baixo, e **Buscar** quando a carta não for reconhecida.
- **Reverse foil e cartas com brilho:** quando a leitura normal não acha o número, o app alterna sozinho entre outros modos a cada quadro: binarização local, que separa o texto do brilho holográfico, e imagem invertida, para texto claro em fundo escuro, como a sigla das promos MEP. Ele junta o que cada modo leu: a sigla de um quadro completa o número lido em outro. Essas cartas podem levar 1 ou 2 segundos a mais; mantenha a carta parada no retângulo.
- **Miniaturas:** imagem oficial da carta (TCGdex; TCGplayer nas japonesas que só ele tem). Sem internet ou sem imagem, aparece uma silhueta na cor do tipo.
- **Lote:** toque numa carta para mudar versão, extras, qualidade, idioma ou quantidade, ou para removê-la.

- **Cartas novas (Escarlate e Violeta em diante):** o app lê a faixa de baixo, por exemplo `MEW PT 063/165`, e acha a carta pela sigla e pelo número.
- **Cartas antigas:** o app lê o número e o total (por exemplo `4/102`) e o nome no topo. Com isso descobre a coleção. Se houver mais de uma possibilidade, mostra uma lista para você escolher.
- **Japonesas modernas (Black & White em diante):** o app lê o código impresso, por exemplo `SV2a 063/165`, e acha a carta nas 95 coleções japonesas do catálogo. O nome em inglês é montado a partir do nome do Pokémon; quando não há tradução (alguns treinadores), a tela da carta pede o nome em inglês, ou exporta em japonês.
- **Japonesas antigas e cartas fora do catálogo:** use **Adicionar manualmente**.
- Na câmera, toque no aviso do topo (o que mostra o status da leitura) para ver o recorte que vai para o leitor e o texto que ele leu. Toque de novo para esconder. Na leitura por foto da galeria, use **Ver o que o leitor viu**.
- A **Sigla na Liga** pode ser corrigida na tela da carta. A correção fica salva para aquela coleção.
- O lote fica salvo no próprio navegador. Baixe ou envie o CSV antes de limpar os dados do Safari.

## One Piece

Toque em **One Piece** no seletor do topo. O botão da câmera e os destaques ficam vermelhos para lembrar em qual Liga o lote vai entrar. O lote de One Piece é separado do de Pokémon, e o CSV sai no formato da LigaOnePiece.

- **Câmera contínua:** igual à do Pokémon. Encaixe a faixa de baixo da carta no retângulo; o app lê o código impresso no canto inferior direito (`OP07-038`, `ST14-001`, `EB01-012`, `PRB01-001`, `P-045`). O código já diz a edição e o número. Para não confundir códigos vizinhos (038 e 036), o mesmo código precisa ser lido duas vezes. Os modos para reverse foil e texto claro também valem aqui.
- **Versões:** pré-release, Release Event, parallel, manga, SP e promos têm o mesmo código impresso da carta normal. A câmera adiciona a versão normal; quando existem outras, o aviso de confirmação diz quantas são. Toque nele (ou em **Editar**) e escolha a sua em **Versão na Liga**.
- **Cartas "conferir":** vieram da base oficial e ainda não estão nos seus exports. Nome e Card # seguem o padrão da Liga, mas vale conferir na primeira importação.
- **Artes alternativas fora do catálogo:** quando a base oficial tem mais artes daquela carta do que o catálogo da Liga, a ficha avisa. Ajuste o **Card #** (o sufixo muda por edição, por exemplo `-PA` na OP-07 e `-AA` na OP-11) ou complete o export dessa edição.
- **Japonesas:** a EB-04 da Liga é só japonesa (Card # com `-JP`); ao escolher essa versão, o idioma muda sozinho para Japonês.
- **Miniaturas:** imagem oficial do site da Bandai. Nas parallels com uma única arte alternativa, aparece a arte alternativa; nas outras versões, a arte normal.

### Dados da LigaOnePiece (pasta `liga-op/`)

Funciona igual à pasta `liga/` do Pokémon: os CSVs exportados da LigaOnePiece têm prioridade e definem edição, sigla, nome, raridade, cor e Card # exatamente como a Liga escreve. Hoje a pasta tem:

- `export-2026-11-08-promos-prerelease.csv`: todas as promos (PC-01) e todas as edições de pré-release e Release Event;
- `export-2026-11-08-colecoes.csv`: até 50 cartas de cada edição normal e os starter decks.

As cartas normais que faltam nas edições vêm da [base oficial](https://github.com/buhbbl/punk-records) (gerada do site da Bandai). Coleções novas que ainda não estão em nenhum export entram com a sigla no padrão da Liga (`OP-18`, `EB-05`, `ST30`) e todas as cartas marcadas para conferir; hoje é o caso da OP-18 (The Dominance of God). Para ter tudo conferido, exporte da Liga as edições completas e envie o arquivo para `liga-op/`. Depois rode **Actions → Atualizar catálogo → Run workflow**.

## Atualizar o catálogo (coleções novas)

O `catalog.json` é gerado a partir do repositório público `tcgdex/cards-database`. O arquivo `.github/workflows/atualizar-catalogo.yml` faz isso sozinho:

- **Toda segunda-feira** o GitHub baixa a base do TCGdex e a base oficial de One Piece, gera os dois catálogos de novo e, se houver coleção nova, salva os arquivos. O site publicado se atualiza em seguida.
- **Para rodar na hora** (por exemplo, no dia de um lançamento): no repositório, abra **Actions → Atualizar catálogo → Run workflow**.

Se a pasta `.github` não subir junto com os outros arquivos (o upload pelo navegador às vezes ignora pastas que começam com ponto), crie o arquivo à mão: **Add file → Create new file**, digite o nome `.github/workflows/atualizar-catalogo.yml`, cole o conteúdo do arquivo e clique em **Commit changes**.

Na primeira vez, confira em **Settings → Actions → General** se a opção **Allow all actions** está marcada.

### Nomes em inglês das japonesas (TCGplayer)

A tarefa semanal também baixa do [TCGCSV](https://tcgcsv.com) (dados públicos do TCGplayer, atualizados todo dia) o nome em inglês de cada carta japonesa. Esses nomes substituem a tradução automática (por exemplo, "Origin Forme Dialga V" em vez de "Dialga V") e acrescentam coleções japonesas que o TCGdex não tem. Se o TCGCSV estiver fora do ar, a tarefa segue sem ele. O resultado aparece no log da tarefa, na linha que começa com "TCGplayer:".

### Dados da Liga (pasta `liga/`)

Os CSVs exportados da LigaPokemon que ficam na pasta `liga/` têm prioridade sobre o TCGdex. Para cada coleção que aparece neles, o app passa a usar:

- a **sigla** da Liga (mesmo que seja diferente da impressa na carta);
- o **nome em português e em inglês**, a **raridade**, a **cor** e o **número** exatamente como a Liga escreve;
- as **cartas que a Liga tem e o TCGdex não tem** naquela coleção (por exemplo, as energias Galaxy Holo dentro da 151);
- **coleções que só existem na Liga**, que entram no catálogo só com os dados dela.

Para cobrir coleções antigas:

1. Na Liga, crie uma coleção separada (por exemplo, "Referência") e use o **cadastro em massa** para adicionar as cartas das coleções antigas.
2. Exporte essa coleção em CSV.
3. No GitHub, abra a pasta `liga/`, clique em **Add file → Upload files** e envie o arquivo. Pode ter vários arquivos; todos são lidos.
4. Rode **Actions → Atualizar catálogo → Run workflow**.

O script também aprende com os exports:

- **Formato do número** de cada coleção: com ou sem zeros à esquerda ("4" na Coleção Básica, "063" na 151) e sufixos ("044JP" na Black Bolt japonesa, "077R" no padrão Equipe Rocket).
- **Versões da mesma coleção** que a Liga separa com outra sigla (Master Ball, Poké Ball, padrão Equipe Rocket, coreana). Elas aparecem na tela da carta em **Versão na Liga**.
- **Subcoleções** com prefixo no número, como Galeria de Treinadores (TG) e Galarian Gallery (GG).

O arquivo `export-2026-11-08-referencia.csv` tem 2 ou 3 cartas de cada uma das 481 coleções da Liga e serve de referência para todas elas.

Para corrigir os dados depois, edite na Liga, exporte de novo e substitua o arquivo na pasta.

O script liga cada coleção da Liga à do TCGdex pelo nome em inglês, depois pela sigla e, por último, pelo nome aproximado mais o total de cartas. Se uma coleção for ligada à errada, force a ligação certa no arquivo `liga/mapa-colecoes.csv`, uma linha por coleção:

```
sigla_liga,id_tcgdex
BS,base1
```

O arquivo já vem com as siglas da Liga para as coleções internacionais de 1996 a 2003 (Base Set = BS, Team Rocket = TR, Wizards Black Star Promos = WPR, Skyridge = SKY etc.). Para as coleções seguintes, acrescente linhas no mesmo formato. Enquanto a sigla de uma coleção não estiver confirmada, a tela da carta mostra um aviso no campo **Sigla na Liga**.

Os ids do TCGdex aparecem no fim do endereço das coleções em tcgdex.dev, ou na saída da tarefa em Actions, que lista como cada sigla foi ligada.

O TCGdex costuma incluir uma coleção nova poucos dias depois do lançamento. Enquanto ela não entra, use **Adicionar manualmente**.
