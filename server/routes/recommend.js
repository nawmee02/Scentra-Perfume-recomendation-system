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

export default router;