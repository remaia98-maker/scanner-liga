# Scanner Liga

App web pessoal para ler cartas de Pokémon TCG pela câmera do celular e gerar um CSV no formato de importação de coleção da LigaPokemon.

## Arquivos

| Arquivo | Para que serve |
| --- | --- |
| `index.html` | O app (tela, câmera, lote e exportação) |
| `core.js` | Lógica de leitura do texto, busca no catálogo e geração do CSV |
| `catalog.json` | Catálogo com 20.650 cartas de 169 coleções (TCGdex), com os nomes da Liga nas coleções do seu export |
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

- **Cartas novas (Escarlate e Violeta em diante):** o app lê a faixa de baixo, por exemplo `MEW PT 063/165`, e acha a carta pela sigla e pelo número.
- **Cartas antigas:** o app lê o número e o total (por exemplo `4/102`) e o nome no topo. Com isso descobre a coleção. Se houver mais de uma possibilidade, mostra uma lista para você escolher.
- **Japonesas e cartas fora do catálogo:** use **Adicionar manualmente**.
- Toque em **Ver o que o leitor viu** para conferir os recortes e o texto lido quando algo der errado.
- A **Sigla na Liga** pode ser corrigida na tela da carta. A correção fica salva para aquela coleção.
- O lote fica salvo no próprio navegador. Baixe ou envie o CSV antes de limpar os dados do Safari.

## Atualizar o catálogo (coleções novas)

O `catalog.json` é gerado a partir do repositório público `tcgdex/cards-database`. O arquivo `.github/workflows/atualizar-catalogo.yml` faz isso sozinho:

- **Toda segunda-feira** o GitHub baixa a base do TCGdex, gera o catálogo de novo e, se houver coleção nova, salva o arquivo. O site publicado se atualiza em seguida.
- **Para rodar na hora** (por exemplo, no dia de um lançamento): no repositório, abra **Actions → Atualizar catálogo → Run workflow**.

Se a pasta `.github` não subir junto com os outros arquivos (o upload pelo navegador às vezes ignora pastas que começam com ponto), crie o arquivo à mão: **Add file → Create new file**, digite o nome `.github/workflows/atualizar-catalogo.yml`, cole o conteúdo do arquivo e clique em **Commit changes**.

Na primeira vez, confira em **Settings → Actions → General** se a opção **Allow all actions** está marcada.

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

Para corrigir os dados depois, edite na Liga, exporte de novo e substitua o arquivo na pasta.

O script liga cada coleção da Liga à do TCGdex pelo nome em inglês, depois pela sigla e, por último, pelo nome aproximado mais o total de cartas. Se uma coleção for ligada à errada, force a ligação certa no arquivo `liga/mapa-colecoes.csv`, uma linha por coleção:

```
sigla_liga,id_tcgdex
BS,base1
```

O arquivo já vem com as siglas da Liga para as coleções internacionais de 1996 a 2003 (Base Set = BS, Team Rocket = TR, Wizards Black Star Promos = WPR, Skyridge = SKY etc.). Para as coleções seguintes, acrescente linhas no mesmo formato. Enquanto a sigla de uma coleção não estiver confirmada, a tela da carta mostra um aviso no campo **Sigla na Liga**.

Os ids do TCGdex aparecem no fim do endereço das coleções em tcgdex.dev, ou na saída da tarefa em Actions, que lista como cada sigla foi ligada.

O TCGdex costuma incluir uma coleção nova poucos dias depois do lançamento. Enquanto ela não entra, use **Adicionar manualmente**.
