# Ajusta Time

Aplicativo desktop, offline, para cadastrar funcionários, montar escalas mensais de folgas e imprimir a escala em A4. Dias normais de trabalho ficam vazios; o banco armazena somente folgas, férias, atestados e faltas.

## Recursos

- Cadastro, edição e exclusão segura de funcionários.
- Escala mensal com 28, 29, 30 ou 31 dias e dias da semana em português.
- Edição automática pelo menu de contexto de cada célula (`F`, `FE`, `AT`, `FA` ou limpar).
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

1. Abra **Funcionários** para manter a lista de pessoas.
2. Em **Escala**, escolha mês e ano.
3. Clique com o botão direito em uma célula e escolha Folga, Férias, Atestado, Falta ou Limpar. A alteração é salva imediatamente.
4. Use **Copiar mês anterior** para substituir o mês atual pelas ocorrências do mês anterior.
5. Use **Imprimir** para abrir a pré-visualização. O botão de impressão da prévia abre a seleção nativa de impressora.

Um funcionário com ocorrências não pode ser excluído, evitando registros órfãos. Limpe as ocorrências correspondentes antes de excluí-lo.

## Backup

- **Backup do banco SQLite:** usa a API de backup do SQLite, adequada mesmo com o banco em uso.
- **Exportar JSON:** grava funcionários, ocorrências e configurações em um arquivo legível.
- **Importar JSON:** valida todo o arquivo antes da operação e substitui os dados em uma única transação. Se qualquer etapa falhar, os dados anteriores são preservados.

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

