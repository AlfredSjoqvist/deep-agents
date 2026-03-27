const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json());
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

app.listen(3000, () => {
  console.log('Sentinel dashboard running at http://localhost:3000');
});
