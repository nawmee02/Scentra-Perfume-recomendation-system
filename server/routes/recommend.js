// server/routes/recommend.js
import express from 'express';
import fetch from 'node-fetch'; // or use global fetch in Node 18+

const router = express.Router();

router.post('/', async (req, res) => {
  const { query, limit } = req.body;
  if (!query) return res.status(400).json({ error: 'Query required' });

  try {
    const mlRes = await fetch('http://localhost:8001/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, k: limit || 5 }),
    });
    const data = await mlRes.json();
    return res.json(data);
  } catch (err) {
    console.error('ML service error', err);
    return res.status(500).json({ error: 'Recommendation service unavailable' });
  }
});

// LLM-powered chat: retrieval + single-call explanation with inventory awareness.
router.post('/chat', async (req, res) => {
  const { query, limit } = req.body;
  if (!query) return res.status(400).json({ error: 'Query required' });

  try {
    const mlRes = await fetch('http://localhost:8001/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, k: limit || 5 }),
    });
    const data = await mlRes.json();
    return res.json(data);
  } catch (err) {
    console.error('ML service error', err);
    return res.status(500).json({ error: 'Recommendation service unavailable' });
  }
});

// Live price lookup for a named perfume.
router.post('/price', async (req, res) => {
  const { name, brand } = req.body;
  if (!name) return res.status(400).json({ error: 'name required' });

  try {
    const mlRes = await fetch('http://localhost:8001/price', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, brand: brand || '' }),
    });
    return res.json(await mlRes.json());
  } catch (err) {
    console.error('ML service error', err);
    return res.status(500).json({ error: 'Price service unavailable' });
  }
});

export default router;