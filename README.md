# 🎓 Sistema de Gestão de Treinamentos

<p align="center">
  <strong>Plataforma web para organização e gerenciamento de treinamentos corporativos.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django">
  <img src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL">
  <img src="https://img.shields.io/badge/Status-Em%20desenvolvimento-blue?style=for-the-badge" alt="Status">
</p>

---

## 📌 Sobre o projeto

O **Sistema de Gestão de Treinamentos** é uma aplicação web desenvolvida em Python com Django, voltada à organização de informações relacionadas a treinamentos, usuários e atividades de capacitação.

O projeto busca centralizar informações, estruturar rotinas administrativas e facilitar o gerenciamento dos registros de treinamento por meio de uma aplicação web.

## ✨ Funcionalidades

- 🔐 Autenticação e gerenciamento de usuários.
- 👤 Modelo de usuário personalizado com Django.
- 📚 Organização de informações relacionadas aos treinamentos.
- 🛠️ Interface administrativa para gerenciamento de registros.
- 📊 Recursos de importação e exportação de dados, conforme disponíveis na implementação.
- 📁 Organização de arquivos estáticos, templates e mídias.
- 🗄️ Integração com banco de dados MySQL.

> As funcionalidades apresentadas devem ser ajustadas conforme os recursos efetivamente implementados na versão publicada.

## 🧰 Tecnologias

| Tecnologia | Finalidade |
|---|---|
| Python | Linguagem principal |
| Django | Framework web |
| MySQL | Persistência de dados |
| HTML e CSS | Estrutura e apresentação |
| JavaScript | Interatividade no navegador |
| Django Admin | Administração dos registros |
| Bibliotecas Python | Recursos complementares |

## 🏗️ Arquitetura do projeto

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

A estrutura é ilustrativa e deve refletir os diretórios efetivamente existentes no repositório.

## 🚀 Como executar localmente

### 1. Pré-requisitos

- Python compatível com as dependências do projeto.
- MySQL Server.
- Git, caso opte por clonar o repositório pelo terminal.

### 2. Obtenha o código

```bash
git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
cd SEU_REPOSITORIO
```

Substitua a URL pelo endereço do repositório.

### 3. Crie um ambiente virtual

**Windows**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux ou macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Instale as dependências

```bash
pip install -r requirements.txt
```

### 5. Configure o ambiente

Copie `.env.example` para `.env` e configure as variáveis necessárias.

Exemplo das variáveis esperadas:

```dotenv
DJANGO_SECRET_KEY=
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306
```

Preencha os valores localmente. Nunca publique o arquivo `.env` nem credenciais reais.

### 6. Prepare o banco de dados

Crie um banco MySQL vazio e configure o acesso por meio das variáveis de ambiente.

Execute as migrações:

```bash
python manage.py migrate
```

### 7. Crie um usuário administrador

```bash
python manage.py createsuperuser
```

### 8. Inicie o servidor

```bash
python manage.py runserver
```

A aplicação estará disponível em:

http://127.0.0.1:8000/

O servidor de desenvolvimento destina-se a testes locais, não à implantação em produção.

## 🖼️ Capturas de tela

Adicione imagens demonstrativas da aplicação nesta seção quando estiverem disponíveis.

Exemplo de organização:

```text
docs/
└── screenshots/
    ├── dashboard.png
    ├── treinamentos.png
    └── usuarios.png
```

Use somente capturas sem dados pessoais, credenciais ou informações corporativas confidenciais.

<!-- Quando houver capturas disponíveis, você poderá inserir:
![Dashboard](docs/screenshots/dashboard.png)
-->

## 🔒 Segurança

Este projeto deve ser configurado com credenciais próprias para cada ambiente.

- Não versionar arquivos `.env`.
- Não publicar senhas, tokens ou chaves secretas.
- Não incluir bancos de dados com informações reais.
- Não compartilhar dados pessoais ou documentos confidenciais.
- Utilizar dados fictícios em demonstrações.
- Manter dependências e configurações de segurança atualizadas.

## 🛣️ Possíveis evoluções

- Aprimoramento de dashboards e indicadores.
- Melhorias na experiência de utilização.
- Ampliação de relatórios gerenciais.
- Automatização de tarefas administrativas.
- Evolução dos recursos de importação e exportação.

Estas são possibilidades futuras, não funcionalidades necessariamente disponíveis na versão atual.

## 👨‍💻 Desenvolvimento

O projeto utiliza uma arquitetura baseada em Django, com separação de responsabilidades entre aplicações, templates e recursos estáticos.

Sugestões e melhorias podem ser registradas por meio de issues e pull requests, conforme as regras do repositório.

## 📄 Licença

A licença deverá ser definida pelo responsável pelo projeto.

Até que uma licença seja adicionada, não presuma que o código esteja autorizado para redistribuição ou uso por terceiros.
