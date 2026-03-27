const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json({ limit: '5mb' }));
app.use(express.static(path.join(__dirname)));

// Proxy endpoint for Bland AI calls (avoids CORS)
app.post('/api/bland/call', async (req, res) => {
  try {
    const resp = await fetch('https://api.bland.ai/v1/calls', {
      method: 'POST',
      headers: {
        'authorization': req.headers['x-bland-key'],
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req.body),
    });
    const data = await resp.json();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Proxy endpoint to check call status
app.get('/api/bland/call/:callId', async (req, res) => {
  try {
    const resp = await fetch(`https://api.bland.ai/v1/calls/${req.params.callId}`, {
      headers: { 'authorization': req.headers['x-bland-key'] },
    });
    const data = await resp.json();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Generate PDF from HTML
app.post('/api/report/pdf', async (req, res) => {
  try {
    const puppeteer = require('puppeteer');
    const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
    const page = await browser.newPage();
    await page.setContent(req.body.html, { waitUntil: 'networkidle0' });
    const pdf = await page.pdf({
      format: 'Letter',
      margin: { top: '0.75in', bottom: '0.75in', left: '0.75in', right: '0.75in' },
      printBackground: true,
    });
    await browser.close();
    res.set({ 'Content-Type': 'application/pdf', 'Content-Disposition': 'attachment; filename="Incident_Report_SENTINEL-2026-0327-001.pdf"' });
    res.send(pdf);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(3000, () => {
  console.log('Sentinel dashboard running at http://localhost:3000');
});
