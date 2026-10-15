# Sistema de Gestão de Treinamentos

Sistema web desenvolvido em Django para apoiar a gestão de treinamentos, usuários, colaboradores e registros de capacitação.

## Sobre o projeto

A aplicação tem como objetivo centralizar informações e facilitar o gerenciamento das atividades de treinamento, oferecendo uma estrutura web com autenticação, administração de dados e recursos para organização das informações.

## Funcionalidades

- Autenticação e gerenciamento de usuários.
- Modelo de usuário personalizado.
- Interface administrativa do Django.
- Gerenciamento de informações relacionadas aos treinamentos.
- Organização de aplicações e templates.
- Importação e exportação de dados, conforme os recursos implementados.
- Configuração de arquivos estáticos e mídias.
- Suporte a banco de dados MySQL.

*As funcionalidades disponíveis dependem da implementação atual do projeto.*

## Tecnologias utilizadas

- **Python**
- **Django**
- **MySQL**
- HTML, CSS e JavaScript
- Django Admin
- Bibliotecas complementares para administração, formulários e importação/exportação de dados.

## Estrutura do projeto

```text
sistema-treinamentos/
├── core/
├── usuarios/
├── treinamento_project/
├── templates/
├── static/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

A estrutura acima é ilustrativa. Os diretórios podem variar conforme a organização atual do projeto.

## Pré-requisitos

Antes de iniciar, instale:

- Python compatível com a versão utilizada no projeto.
- MySQL Server.
- Git (opcional, para clonar o repositório pelo terminal).

## Instalação e configuração

### 1. Obtenha o projeto

Clone o repositório:

```bash
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
cd SEU_REPOSITORIO
```

Substitua a URL pelo endereço real do repositório.

### 2. Crie um ambiente virtual

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Linux ou macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Copie o arquivo `.env.example` para `.env` e preencha os valores necessários para seu ambiente local.

As variáveis podem incluir:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

Gere uma chave secreta exclusiva para seu ambiente. Nunca compartilhe o arquivo `.env` ou credenciais reais.

### 5. Configure o banco de dados

Crie um banco MySQL vazio e configure as variáveis de conexão no arquivo `.env`.

O usuário do banco deve possuir apenas as permissões necessárias para executar a aplicação.

### 6. Execute as migrações

```bash
python manage.py migrate
```

### 7. Crie um usuário administrador

```bash
python manage.py createsuperuser
```

### 8. Inicie o servidor de desenvolvimento

```bash
python manage.py runserver
```

Acesse a aplicação em:

http://127.0.0.1:8000/

O servidor de desenvolvimento não deve ser utilizado como servidor de produção.

## Arquivos estáticos

Os arquivos originais de CSS, JavaScript e imagens devem ser mantidos no diretório `static/`.

Em ambientes de implantação que exigem a coleta dos arquivos estáticos, execute:

```bash
python manage.py collectstatic
```

A pasta gerada `staticfiles/` não precisa ser versionada no repositório.

## Segurança e privacidade

Este repositório não deve conter:

- Senhas ou chaves secretas.
- Arquivos `.env`.
- Bancos de dados com informações reais.
- Dados pessoais de usuários ou colaboradores.
- Tokens de acesso.
- Backups, relatórios internos ou anexos confidenciais.

Utilize dados fictícios para testes e demonstrações.

## Desenvolvimento

Contribuições e sugestões podem ser organizadas por meio de branches e pull requests, conforme as permissões e as regras definidas para o repositório.

Antes de propor alterações, valide a aplicação e revise os arquivos modificados para evitar a inclusão acidental de informações sensíveis.

## Licença

A licença deste projeto deve ser definida pelo responsável pelo repositório.

Até que uma licença seja incluída, não presuma que o código esteja liberado para redistribuição ou uso por terceiros.
