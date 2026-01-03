# Video Generator - Sistema de Geração Automática de Vídeos

Sistema completo de geração de vídeos automáticos que transforma texto em vídeo narrado com imagens geradas por IA e música de fundo.

## Funcionalidades

- **Narração por IA**: Converte texto em áudio natural usando ElevenLabs
- **Transcrição Precisa**: Timestamps palavra por palavra via AssemblyAI
- **Análise de Cenas**: Divisão inteligente em cenas usando Google Gemini
- **Imagens por IA**: Geração de imagens cinematográficas via WaveSpeed Flux
- **Música de Fundo**: Biblioteca própria ou geração via IA (Suno)
- **Composição Profissional**: FFMPEG com transições, efeitos Ken Burns, vinheta

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React/Next.js)                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ Config APIs │ │Upload Music │ │   Configurações FFMPEG  ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │              Editor de Texto + Preview                   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │ API REST
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Text     │ │ Audio    │ │ Image    │ │ Video          │  │
│  │ Processor│ │ Pipeline │ │ Pipeline │ │ Composer       │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Requisitos

- Ubuntu 22.04 (ou similar)
- Python 3.11+
- Node.js 20+
- FFMPEG
- Docker & Docker Compose (opcional)

## Instalação

### Opção 1: Docker (Recomendado)

```bash
# Clonar o repositório
git clone <repo-url>
cd video-generator

# Configurar variáveis de ambiente
cp backend/.env.example backend/.env
# Editar backend/.env com suas API keys

# Iniciar com Docker
docker-compose up -d

# Acessar
# Frontend: http://localhost:3000
# Backend: http://localhost:8000/docs
```

### Opção 2: Instalação Manual

```bash
# Instalar dependências do sistema
sudo apt update
sudo apt install -y ffmpeg python3-pip nodejs npm

# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
# Editar .env com suas API keys
uvicorn src.main:app --reload

# Frontend (em outro terminal)
cd frontend
npm install
npm run dev
```

## Configuração das APIs

O sistema utiliza várias APIs externas:

| API | Uso | Obrigatório |
|-----|-----|-------------|
| ElevenLabs | Geração de narração | Sim |
| AssemblyAI | Transcrição com timestamps | Sim |
| Google Gemini | Análise de cenas e prompts | Sim |
| WaveSpeed | Geração de imagens | Sim |
| Suno | Geração de música (opcional) | Não |

Configure todas as API keys no painel de configurações do frontend ou no arquivo `.env`.

## Fluxo de Geração

1. **Texto** → Dividido em chunks (máx 2500 caracteres)
2. **ElevenLabs** → Gera áudio para cada chunk
3. **Concatenação** → Áudios unidos em arquivo único
4. **AssemblyAI** → Transcrição com timestamps por palavra
5. **Gemini** → Divide em cenas, gera prompts de imagem, classifica moods
6. **Música** → Selecionada da biblioteca ou gerada por IA
7. **WaveSpeed** → Gera imagem para cada cena
8. **Mixagem** → Narração + música com ducking
9. **FFMPEG** → Composição final com transições e efeitos

## Estrutura de Pastas

```
/video-generator/
├── frontend/           # Next.js 14 + React + Tailwind
├── backend/            # FastAPI + Python
├── storage/
│   ├── music/         # Biblioteca de músicas (por mood)
│   ├── temp/          # Arquivos temporários
│   ├── outputs/       # Vídeos gerados
│   └── cache/         # Cache de requisições
├── docker-compose.yml
└── README.md
```

## Configurações de Vídeo (FFMPEG)

- **Resolução**: 1920x1080, 1080x1920 (vertical), 1280x720
- **FPS**: 24, 30, 60
- **Transições**: fade, dissolve, wipe, slide, circle, pixelize
- **Efeitos**: Ken Burns (zoom/pan), vinheta, grain
- **Áudio**: AAC/MP3, normalização LUFS, ducking automático

## Desenvolvimento

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## API Endpoints

### Configuração
- `GET /api/config` - Obter configurações
- `PUT /api/config` - Atualizar configurações
- `POST /api/config/test-api` - Testar conexão de API
- `GET /api/config/credits` - Obter créditos das APIs

### Música
- `GET /api/music` - Listar músicas
- `POST /api/music/upload` - Upload de música
- `PUT /api/music/{id}` - Atualizar metadados
- `DELETE /api/music/{id}` - Remover música

### Vídeo
- `POST /api/video/analyze-text` - Analisar texto
- `POST /api/video/generate` - Iniciar geração

### Jobs
- `GET /api/jobs` - Listar jobs
- `GET /api/jobs/{id}/status` - Status do job
- `GET /api/jobs/{id}/result` - Resultado do job
- `GET /api/jobs/{id}/download` - Download do vídeo

## Licença

MIT License - Veja o arquivo LICENSE para detalhes.
