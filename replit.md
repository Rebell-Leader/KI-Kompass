# Overview

KI Kompass (AI Compass) is a Munich-focused relocation and integration assistant application built with Flask. The application provides personalized guidance for people relocating to Munich, Germany, through AI-powered assistance and step-by-step integration pipelines.

# System Architecture

## Frontend Architecture
- **Technology**: HTML templates with Jinja2 templating engine
- **Styling**: Custom CSS with Bootstrap components
- **JavaScript**: Vanilla JavaScript for interactive features
- **Key Pages**: Landing page, dashboard, chat interface, profile management, onboarding flow

## Backend Architecture
- **Framework**: Flask (Python web framework)
- **Architecture Pattern**: Modular design with blueprints for route organization
- **Database ORM**: SQLAlchemy with Flask-SQLAlchemy extension
- **Session Management**: Flask sessions with secure secret key
- **Authentication**: Password hashing with Werkzeug security utilities

## Database Design
- **Primary Database**: PostgreSQL with SQLAlchemy ORM
- **Models**: User, IntegrationPipeline, ActionStep, TaskStatus, ChatMessage
- **Relationships**: One-to-many between users and pipelines, many-to-many through task statuses

# Key Components

## User Management System
- User registration and authentication
- Profile management with relocation-specific fields (nationality, visa type, arrival date, family status)
- Onboarding flow to collect user preferences and circumstances

## Integration Pipeline Engine
- **Purpose**: Generates personalized relocation checklists based on user profile
- **Logic**: Selects relevant action steps based on visa type, family status, employment situation
- **Progress Tracking**: Calculates completion percentage and manages task deadlines

## AI Assistant Service
- **LLM Integration**: Supports both OpenAI and Featherless AI as providers
- **Conversation Management**: Maintains chat history with conversation IDs
- **Context Awareness**: Uses user profile information to provide personalized responses
- **Knowledge Base**: Integrated with Langchain for enhanced responses

## Action Steps Management
- **Pre-defined Templates**: Database populated with Munich-specific relocation tasks
- **Categorization**: Tasks organized by category (pre-arrival, registration, housing, etc.)
- **Dependencies**: Tasks can have prerequisites and timeline constraints
- **Customization**: Steps selected based on user profile characteristics

# Data Flow

## User Registration Flow
1. User submits registration form
2. Password is hashed and user record created
3. User redirected to onboarding to complete profile
4. Pipeline generation triggered after profile completion

## Pipeline Generation Flow
1. User profile analyzed for relevant characteristics
2. Action steps filtered based on visa type, family status, employment
3. Tasks scheduled based on arrival date and timeline offsets
4. TaskStatus records created linking user's pipeline to selected steps

## AI Chat Flow
1. User submits query through chat interface
2. Message stored in database with conversation ID
3. User profile context added to AI prompt
4. LLM response generated and stored
5. Response returned to user interface

# External Dependencies

## AI/LLM Services
- **Primary**: Featherless AI (DeepSeek-V3 model)
- **Fallback**: OpenAI GPT models
- **Embeddings**: FastEmbed with Nomic AI embeddings or OpenAI embeddings
- **Vector Storage**: Qdrant for semantic search capabilities

## Database Infrastructure
- **PostgreSQL**: Primary data storage
- **Environment Variables**: Database connection configured via PGUSER, PGPASSWORD, PGHOST, PGPORT, PGDATABASE

## Frontend Libraries
- **Bootstrap**: UI components and responsive design
- **Feather Icons**: Icon library for UI elements
- **Inter Font**: Typography from Google Fonts

# Deployment Strategy

## Environment Configuration
- **Database**: PostgreSQL with connection pooling and health checks
- **Session Security**: Configurable secret key via SESSION_SECRET environment variable
- **API Keys**: Support for both OPENAI_API_KEY and FEATHERLESS_API_KEY
- **WSGI**: ProxyFix middleware for deployment behind reverse proxy

## Database Initialization
- **Auto-migration**: Database tables created automatically on startup
- **Data Seeding**: Action steps populated from predefined templates
- **Connection Management**: Pool recycling and pre-ping for reliability

## Static Assets
- **CSS**: Modular stylesheets for different features (main, chat, pipeline)
- **JavaScript**: Feature-specific scripts for enhanced interactivity
- **Templates**: Jinja2 templates with inheritance for consistent UI

# Keeping Data Fresh

Task details (working hours, fees, required documents) and the AI knowledge
base are grounded in official sources. Each action step stores a `source_url`
and a `last_verified` date, shown to users on the task cards.

Run `flask refresh-knowledge` to fetch the current text of every official
source page into the `knowledge_documents` table; the chat assistant answers
from that content (with source citations) and each step's `last_verified`
date is bumped when its source is fetched successfully. Schedule this command
(e.g. daily via cron or a scheduled deployment) to keep the data current.
When the table is empty, a curated built-in knowledge base is used as fallback.

# Changelog

Changelog:
- June 29, 2025. Initial setup
- July 7, 2026. MVP fixes, security hardening (CSRF, rate limiting), Alembic
  migrations, official-source data provenance and knowledge refresh pipeline.

# User Preferences

Preferred communication style: Simple, everyday language.