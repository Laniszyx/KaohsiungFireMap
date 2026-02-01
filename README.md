# 高雄消防即時案件地圖 (Kaohsiung Fire Incidents Map)

This project visualizes real-time fire and emergency incidents in Kaohsiung City, Taiwan.

## Features
- **Automated Scraping**: Python script fetches data from Kaohsiung Fire Department every 10 minutes.
- **GitHub Actions**: Fully automated workflow (no server required).
- **Interactive Map**: Leaflet.js map showing incidents from the last 2 hours.
- **Visual Distinction**:
    - 🔴 **Red Ring**: Recent incidents (< 30 mins).
    - 🔵 **Blue Marker**: Older incidents (> 30 mins).
    - ⭕ **Area Circle**: Incidents with vague addresses (e.g., district only).

## Setup
### Local Development
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run scraper:
   ```bash
   python scraper.py
   ```
   This will generate `data.json`.
3. Open `index.html` in your browser to view the map.

### Deployment (GitHub Pages)
1. Push this repository to GitHub.
2. Go to **Settings > Pages**.
3. Set **Source** to `main` branch.
4. The site will be live at `https://<your-username>.github.io/<repo-name>/`.

### Configuration
- **Scraper**: `scraper.py` parses the specific KFD URL.
- **Workflow**: `.github/workflows/main.yml` runs every 10 minutes.
- **Geocoding**: Currently uses a fallback "District Center" mapping in `index.html`. For precise geocoding, implement an API in `scraper.py`.

## Data Source
Kaohsiung City Fire Department: [Real-time Incidents](https://119dts.fdkc.gov.tw/tyfdapp/webControlKC?page=Tfqve7Vz8sjTOllavM2iqQ==&f=IC2SZJqIMDj1EwKMezrgvw==)
