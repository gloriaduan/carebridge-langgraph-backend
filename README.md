# CareConnect - A Toronto Community Resources Agent

A LangGraph-powered intelligent agent that helps users find community and social support services in the Greater Toronto Area. The system uses Toronto's Open Data API and Google Maps to provide real-time information about shelters, family centers, and other essential services.

## 🌟 Features

- **Smart Query Processing**: Validates and processes natural language queries for community services
- **Multi-Source Data Integration**: Combines Toronto Open Data API with Google Maps for comprehensive results
- **Location-Based Filtering**: Filters results by proximity to user location using geocoding
- **Real-Time Occupancy Data**: Provides current shelter availability and occupancy rates
- **Multi-Language Support**: Supports 25+ languages for family center programs
- **Caching Layer**: Redis-based caching for improved performance
- **Real-Time Updates**: WebSocket-based progress updates during query processing

## 🏗️ Architecture

The application uses a LangGraph state machine with the following workflow:

```
Query Input → Validation → API Search → Evaluation → Web Search (if needed) → Response Generation
```

### Core Components

- **Query Validation**: Classifies queries as valid community service requests
- **API Search**: Retrieves data from Toronto Open Data portal
- **Evaluation**: Determines if additional web search is needed
- **Web Search**: Google Maps integration for additional results
- **Response Generation**: Structured output with contact information

## 🚀 Deployment

### Backend (Google Cloud Platform)
- **Platform**: Google Cloud Run
- **Language**: Python with FastAPI
- **WebSockets**: Socket.IO for real-time communication
- **Caching**: Redis for performance optimization

### Frontend (Vercel)
- **Platform**: Vercel
- **Framework**: React/Next.js (inferred from Socket.IO integration)
- **Real-time**: Socket.IO client for live updates

## 📊 Supported Services

### Shelters
- **Sectors**: Families, Mixed Adult, Men, Women, Youth
- **Service Types**: Shelter, Motel/Hotel Shelter, 24-Hour Respite Site, etc.
- **Real-time Data**: Occupancy rates, capacity, availability

### Children & Family Centers
- **Language Programs**: 25+ supported languages including Arabic, Mandarin, Spanish, etc.
- **Specialized Programs**: French language programs, Indigenous programs
- **Services**: Early childhood development, family support, parenting programs
