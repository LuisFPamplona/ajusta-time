# Ajusta Time

Aplicativo desktop, offline, para cadastrar funcionários, montar escalas mensais de folgas e imprimir a escala em A4. Dias normais de trabalho ficam vazios; o banco armazena somente folgas, férias, atestados e faltas.

## Recursos

- Cadastro, edição e exclusão segura de funcionários.
- Folga semanal padrão opcional para cada funcionário, de segunda a domingo.
- Gestão de períodos de férias e atestados, com filtros, situação e observações.
- Calendário mensal responsivo, com contagem diária de folgas e dias da semana em português.
- Cards com total de folgas, dia com mais folgas e quantidade de funcionários.
- Seleção dos funcionários de folga em um diálogo aberto pelo clique no dia.
- Exceções persistentes para trabalhar em um dia que seria uma folga padrão.
- Preservação de férias, atestados e faltas existentes durante a edição das folgas.
- Cópia transacional do mês anterior, ignorando datas inexistentes.
- Pré-visualização e impressão nativas do Qt em A4 horizontal, com todos os dias na mesma largura e paginação vertical.
- Nome da empresa, título e opções de legenda, assinatura e data de impressão.
- Backup consistente do SQLite, exportação JSON e importação JSON validada e transacional.

## Requisitos

- Python 3.10 ou mais recente
- Windows, Linux ou macOS com suporte ao PySide6

## Instalação

No diretório do projeto, crie e ative um ambiente virtual.

Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Execução

```bash
python main.py
```

Na primeira execução o aplicativo cria automaticamente `data/escala.db`, as tabelas necessárias e três funcionários de exemplo. Os exemplos são incluídos uma única vez e podem ser editados ou excluídos.

O arquivo `data/escala.db` contém os dados reais e não é versionado pelo Git. Faça backups regulares pela tela **Configurações**.

## Uso básico

1. Abra **Funcionários** para manter a lista de pessoas e, opcionalmente, definir a folga semanal padrão.
2. Em **Escala**, escolha mês e ano ou use as setas para navegar.
3. Em **Afastamentos**, cadastre períodos de férias ou atestado. Cada período pode ter um único dia e também pode atravessar meses ou anos.
4. Clique em um dia do calendário, marque os funcionários de folga e selecione **Salvar**. Funcionários afastados aparecem bloqueados e devem ser alterados pela aba **Afastamentos**.
5. Use **Copiar mês anterior** para substituir as ocorrências manuais do mês atual pelas do mês anterior; afastamentos permanecem preservados.
6. Use **Imprimir** para abrir a pré-visualização. O botão de impressão da prévia abre a seleção nativa de impressora.

Um funcionário com ocorrências não pode ser excluído, evitando registros órfãos. Limpe as ocorrências correspondentes antes de excluí-lo.

As folgas padrão são geradas como `DAY_OFF` sem sobrescrever ocorrências existentes. Se uma folga padrão for desmarcada no diálogo do dia, o aplicativo registra internamente uma exceção de trabalho para que ela não reapareça ao recarregar o calendário. Ao trocar ou remover o dia padrão, somente folgas automáticas futuras são removidas; histórico e decisões manuais permanecem preservados.

## Backup

- **Backup do banco SQLite:** usa a API de backup do SQLite, adequada mesmo com o banco em uso.
- **Exportar JSON:** grava funcionários, folgas padrão, ocorrências com suas origens e configurações em um arquivo legível.
- **Importar JSON:** valida todo o arquivo antes da operação e substitui os dados em uma única transação. Se qualquer etapa falhar, os dados anteriores são preservados.

Backups JSON anteriores à inclusão das folgas padrão e dos afastamentos continuam compatíveis: dias padrão ausentes são interpretados como `Nenhuma`, origens ausentes como `MANUAL` e a lista de afastamentos ausente como vazia.

Importar JSON substitui todos os dados atuais; crie um backup antes quando necessário.

## Estrutura

```text
main.py
app/
  database/
    connection.py
    schema.py
    repositories/
  services/
  ui/
  utils/
data/
tests/
```

A interface não executa SQL. Repositórios concentram o acesso ao banco, serviços aplicam as regras e as telas cuidam da interação com o usuário.

A paleta visual é centralizada em `app/ui/theme.py`. Novos componentes devem usar
os tokens de `COLORS` e os papéis de `QPalette`, evitando cores locais ou herdadas
do tema do sistema operacional. O tema é aplicado ao `QApplication`, inclusive em
menus, listas suspensas, dicas e outras janelas auxiliares do Qt.

## Testes

```bash
python -m unittest discover -v
```

## Empacotamento futuro com PyInstaller

Com o ambiente virtual ativo:

```powershell
pyinstaller --noconfirm --windowed --name "Ajusta Time" main.py
```

O executável será criado em `dist/Ajusta Time/`. O arquivo `.spec`, `build/` e `dist/` são artefatos locais e estão ignorados pelo Git. Antes de distribuir, valide em uma máquina Windows limpa a escrita na pasta `data`, a pré-visualização e uma impressão real.
