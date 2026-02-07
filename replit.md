# Pazaryeri Veri Analiz Platformu

## Overview
The Marketplace Data Analysis Platform is designed to empower marketplace sellers and marketing agencies with data-driven decision-making capabilities. It achieves this by scraping product data from major Turkish marketplaces, analyzing market trends, and delivering AI-powered insights. The platform's vision is to become a crucial tool for competitive analysis, strategic pricing, and understanding market dynamics within the e-commerce landscape.

## User Preferences
- English language UI with Palantir-style dark theme
- Focus on Hepsiburada marketplace initially
- Limit to 8 products per search to manage costs
- ScraperAPI as primary (cheaper), Bright Data for fallback

## UI Theme
- Dark color palette: dark-900 (#0a0b0d) to dark-300 (#3d434e)
- Accent color: Cyan (#00d4ff) for primary actions and highlights
- Status colors: Success green, Warning orange, Danger red with glow variants
- Reusable components: card-dark, btn-primary/secondary, input-dark, table-dark, badges, stat-card
- Subtle animations: fade-in, slide-in, pulse-glow effects

## System Architecture
The platform is built with a clear separation of concerns, featuring a FastAPI backend and a React frontend. It employs a robust, two-stage scraping strategy for comprehensive data collection and a modular proxy architecture for reliable data acquisition.

**UI/UX Decisions:**
The frontend utilizes React, Vite, and TailwindCSS for a modern, responsive, and efficient user experience. Key UI components include:
- A dashboard for overall market insights.
- Product listings and detailed product pages with tabs for various data points.
- Dedicated pages for "Reklamlar" (sponsored products) and "Fiyat Takip" (price monitoring).
- Data visualization through charts for price and rating trends (Plotly.js).

**Technical Implementations & Feature Specifications:**
- **Two-Stage Scraping:** Products are first identified from search/listing pages, then individual product detail pages are visited to extract extensive data. This includes parsing `utagData` JavaScript objects, JSON-LD schema, and various HTML elements to gather product name, brand, category, price, SKU, barcode, seller information, ratings, reviews, stock status, discounted prices, coupons, and campaign details.
- **Price Monitoring System:** Allows distributors to track seller prices across multiple platforms (Hepsiburada, Trendyol) for specific SKUs. It supports bulk product imports and initiates tasks for fetching price data, capturing details like merchant name, price, stock, buybox order, and shipping information.
- **Sponsored Ads Tracking:** Identifies individual sponsored products and groups them to track brand advertisers. This involves parsing advertisement-specific HTML classes and decoding tracking URLs to extract real product information and associated seller data.
- **AI Analysis:** Integrates OpenAI's GPT-4o-mini for generating insights from collected product data.
- **Modular Proxy System:** Features an "auto" mode that prioritizes ScraperAPI (cheaper) and falls back to Bright Data (premium, for bot protection bypass) if ScraperAPI fails. This system includes debug logging and HTML saving for troubleshooting scraping issues.
- **URL Scraper:** A generic URL scraping system that can scrape any product URL. Supports single URL input, bulk JSON input, and CSV file upload. Uses ScraperAPI to fetch pages, then extracts product data via HTML meta tags, JSON-LD schema, Open Graph data, and general HTML parsing. Results are stored in DB and downloadable as JSON. DB models: `ScrapeJob`, `ScrapeResult`. API routes at `/api/url-scraper/`.
- **Database Schema:** Designed to store rich product information, including `Products`, `ProductSnapshots`, `ProductSellers`, `ProductReviews`, `SponsoredBrandAds`, `ScrapeJob`, and `ScrapeResult`. This allows for historical tracking of prices, ratings, and seller activities.
- **Backend Services:** Implemented with FastAPI, utilizing background tasks for asynchronous operations like scraping. SQLAlchemy is used for ORM with PostgreSQL.
- **Frontend Services:** Uses React with TypeScript, TailwindCSS, and a custom API client for interacting with the backend.

**System Design Choices:**
- **Containerization Readiness:** Though not explicitly stated, the project structure implies a readiness for containerization with separate frontend and backend folders.
- **Asynchronous Operations:** Leverages FastAPI's background tasks for non-blocking operations, crucial for long-running scraping processes.
- **Robust Error Handling:** The proxy system incorporates fallback logic and debug logging to ensure resilience against scraping failures and bot detection.
- **Extensible Data Model:** The database schema is designed to accommodate various product attributes and relationships, supporting future expansions.

## External Dependencies
- **Database:** PostgreSQL (Replit built-in)
- **AI Service:** OpenAI (GPT-4o-mini)
- **Proxy Services:**
    - ScraperAPI (Primary for cost-effective scraping)
    - Bright Data Residential Proxy (Fallback for advanced bot protection bypass, especially with Playwright)
- **Frontend Libraries:**
    - React 18
    - TypeScript
    - TailwindCSS v4
    - Plotly.js (for charting)
    - React Router
- **Backend Libraries:**
    - Python 3.11
    - FastAPI
    - SQLAlchemy
    - Playwright (for advanced web scraping, often with Bright Data)
    - playwright-stealth (for bot detection evasion)
    - BeautifulSoup4 (for HTML parsing)