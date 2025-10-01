# Fact-Checking Telegram Bot - Claude Instructions

## Project Overview
This is a production-ready Telegram fact-checking bot with two-stage analysis system using OpenAI GPT-5 and web search. The bot monitors Telegram channels, filters spam/misinformation, and categorizes messages automatically.

## Architecture
- **Two-stage fact-checking**: Content analysis → intelligent source selection → fact-checking with web search
- **Manual commands**: `/check` for testing individual messages, `/help` for assistance
- **Docker support**: Full containerization with logging and volume management
- **Comprehensive logging**: Detailed message processing with debug information

## Key Files Structure
```
├── main.py                  # Main application entry point
├── src/                     # Core source code
│   ├── config.py           # Configuration management
│   ├── two_stage_filter.py # Two-stage fact-checking system
│   ├── debug_processor.py  # Message processing with debug info
│   ├── command_handler.py  # Bot commands (/check, /help)
│   ├── sources_config.py   # Source domain management
│   └── telegram_client.py  # Telegram API wrapper
├── tests/                   # Test suite
├── logs/                    # Application logs (Docker volume)
├── data/                    # Telegram sessions (Docker volume)
├── Dockerfile              # Multi-stage Docker build
├── docker-compose.yml      # Production deployment config
└── run_tests.py            # Test runner
```

## Development Commands

### Local Development
```bash
# Setup environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run application
python main.py

# Run tests
python run_tests.py
# Or individual tests:
python tests/test_config.py
python tests/test_check_command.py
python tests/test_two_stage.py
```

### Docker Development
```bash
# Build image
docker build -t fact-checker .

# Run with docker-compose (recommended)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Testing Strategy

### Test Files
- `test_config.py`: Configuration validation
- `test_check_command.py`: Manual /check command testing
- `test_two_stage.py`: Two-stage filtering system testing

### Mock Testing
All tests use mock objects to avoid external API calls during testing:
- MockBot for Telegram interactions
- MockMessage for simulating user input
- Timeout handling for OpenAI API calls

## Configuration Management

### Required Environment Variables (.env)
```bash
# Telegram
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token
TARGET_CHAT_ID=your_target_chat_id

# OpenAI
OPENAI_API_KEY=your_openai_key

# Channels (comma-separated)
CHANNELS=@channel1,@channel2
```

### Optional Settings
```bash
GPT_MODEL=gpt-5-turbo-2024-11-20  # OpenAI model
FACT_CHECK_MODE=two_stage          # Filtering mode
DEBUG_MODE=true                    # Enable debug info
SHOW_ALL_MESSAGES=true            # Show hidden messages too
SEND_DEBUG_INFO=true              # Send debug to chat
MAX_SOURCE_DOMAINS=20             # Max domains for fact-checking
STAGE2_INITIAL_DOMAIN_LIMIT=8     # Domains in first stage-2 attempt
STAGE2_RETRY_DOMAIN_LIMIT=5       # Domains in retry attempt
FACT_CHECK_TIMEOUT=45             # Timeout per attempt (seconds)
FACT_CHECK_MODEL=gpt-4o                # Responses model for stage 2 web search
WEB_SEARCH_EFFORT=medium          # Reasoning effort for web search (low/medium/high)
```

## Core Components

### Two-Stage Filtering (`two_stage_filter.py`)
1. **Stage 1**: Analyzes content to select appropriate fact-checking sources
2. **Stage 2**: Performs web search on selected domains for fact verification
3. **Fallback**: Quick classification if web search times out

### Source Management (`sources_config.py`)
- Categorized domains: general_news, technology, finance, science
- Company-specific patterns: Discord → discord.com, Google → blog.google.com
- Automatic source selection based on content analysis

### Command System (`command_handler.py`)
- `/check <message>`: Manual fact-checking with full two-stage analysis
- `/help`: Comprehensive usage instructions
- Same analysis pipeline as automatic monitoring

## Debugging and Logging

### Log Levels
- **INFO**: General operation, message processing
- **WARNING**: Timeouts, fallback usage
- **ERROR**: API failures, critical errors

### Debug Information
When `DEBUG_MODE=true`:
- Full message content and analysis steps
- Stage timing (Stage 1 + Stage 2 execution time)
- Source selection reasoning
- Fallback usage indicators
- Web search status

### Log File Location
- Local: `logs/fact_checker.log`
- Docker: Mounted volume with rotation (50MB × 3 files)

## Production Deployment

### Docker Production
```bash
# Production startup
docker-compose up -d

# Monitor
docker-compose ps
docker-compose logs -f

# Update
docker-compose pull
docker-compose up -d --build
```

### Health Checks
- Container health check every 30s
- Application startup period: 40s
- Automatic restart on failure

## Troubleshooting

### Common Issues
1. **Bot not responding**: Check TARGET_CHAT_ID and bot permissions
2. **OpenAI timeouts**: Verify API key and GPT-5 access
3. **Telegram errors**: Check API credentials and channel access
4. **Import errors**: Ensure proper PYTHONPATH in Docker

### Debug Steps
1. Check configuration: `python tests/test_config.py`
2. Test commands: `python tests/test_check_command.py`
3. Verify logs: `tail -f logs/fact_checker.log`
4. Docker health: `docker-compose ps`

## Code Maintenance

### Adding New Sources
1. Edit `src/sources_config.py`
2. Add domains to appropriate categories
3. Update company-specific patterns if needed
4. Restart application

### Adding New Commands
1. Add method to `CommandHandler` class
2. Register handler in `main.py`
3. Update `/help` command description
4. Add tests in `tests/`

### Modifying Filters
- Main logic in `two_stage_filter.py`
- Stage 1: Source selection prompts
- Stage 2: Fact-checking prompts
- Timeout handling with fallbacks

## Performance Notes
- Docker image: ~207MB (multi-stage build)
- Memory usage: ~256MB baseline, ~512MB limit
- API timeouts: 60s for OpenAI web search
- Log rotation: 50MB per file, 3 files max

## Security Considerations
- Non-root user in Docker container
- Environment variables for secrets
- Read-only mounts for configuration
- No hardcoded API keys in code
- .gitignore excludes sensitive files

This documentation should provide context for future development and maintenance of the fact-checking bot system.
